"""HTTP API: вакансии, кандидаты, парсинг HH, матчинг, навыки, эмбеддинги."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.schemas import (
    VacancyResponse,
    CandidateResponse,
    MatchResult,
    ParsedVacancy,
    ParsedResume,
    NerSpan,
    SkillExtractionResult,
)
from app.services.embeddings import EmbeddingService
from app.services.matching import MatchingService, CandidateRanker
from app.services.skills import SkillsService
from app.services.skill_extractor import SkillExtractor
from app.services.database import DatabaseService
from app.services.vacancy_match_skills import merge_skills_from_vacancy_description


router = APIRouter()

skills_service = SkillsService()
skill_extractor = SkillExtractor(skills_service=skills_service)


@router.get("/stats")
async def get_statistics():
    """Статистика БД."""
    with DatabaseService() as db:
        return db.get_statistics()


@router.get("/vacancies", response_model=List[VacancyResponse])
async def get_vacancies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: bool = True
):
    """Список вакансий."""
    with DatabaseService() as db:
        vacancies = db.get_all_vacancies(limit=limit, offset=offset, is_active=is_active)
        return [db.vacancy_to_response(v) for v in vacancies]


@router.get("/vacancies/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(vacancy_id: int):
    """Вакансия по id; навыки из описания дописываются в карточку."""
    with DatabaseService() as db:
        vacancy = db.get_vacancy_by_id(vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=404, detail="Vacancy not found")
        db.persist_vacancy_skills_from_description(vacancy_id)
        db.session.commit()
        vacancy = db.get_vacancy_by_id(vacancy_id)
        return db.vacancy_to_response(vacancy)


@router.get("/candidates", response_model=List[CandidateResponse])
async def get_candidates(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    specialization: Optional[str] = None
):
    """Список кандидатов."""
    with DatabaseService() as db:
        candidates = db.get_all_candidates(
            limit=limit,
            offset=offset,
            specialization=specialization
        )
        return [db.candidate_to_response(c) for c in candidates]


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(candidate_id: int):
    """Кандидат по id."""
    with DatabaseService() as db:
        candidate = db.get_candidate_by_id(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return db.candidate_to_response(candidate)


class ParseHHRequest(BaseModel):
    query: str
    area: int = 113
    per_page: int = 10


class ParseHHResponse(BaseModel):
    status: str
    vacancies_parsed: int
    vacancies_saved: int
    errors: List[str] = []


@router.post("/parse/hh/vacancies", response_model=ParseHHResponse)
async def parse_hh_vacancies(request: ParseHHRequest):
    """Парсинг вакансий HH и сохранение в БД (per_page ≤ 50)."""
    from app.parsers import HHVacancyParser

    errors = []
    vacancies_parsed = 0
    vacancies_saved = 0

    try:
        async with HHVacancyParser() as parser:
            parsed_vacancies = await parser.parse_list(
                query=request.query,
                area=request.area,
                per_page=min(request.per_page, 50)
            )
            vacancies_parsed = len(parsed_vacancies)

            with DatabaseService() as db:
                for pv in parsed_vacancies:
                    try:
                        db.create_vacancy_from_parsed(pv)
                        vacancies_saved += 1
                    except Exception as e:
                        errors.append(f"Ошибка сохранения {pv.title}: {str(e)}")

        return ParseHHResponse(
            status="success" if vacancies_saved > 0 else "partial",
            vacancies_parsed=vacancies_parsed,
            vacancies_saved=vacancies_saved,
            errors=errors
        )

    except Exception as e:
        return ParseHHResponse(
            status="error",
            vacancies_parsed=vacancies_parsed,
            vacancies_saved=vacancies_saved,
            errors=[str(e)]
        )


@router.post("/parse/hh", response_model=ParseHHResponse, include_in_schema=False)
async def parse_hh_vacancies_alias(request: ParseHHRequest):
    """Алиас POST /parse/hh/vacancies."""
    return await parse_hh_vacancies(request)


class ParseHHResumesRequest(BaseModel):
    query: str
    area: int = 113
    per_page: int = 10
    max_pages: int = 1
    search_field: str = "title"
    logic: str = "normal"


class ParseHHResumesResponse(BaseModel):
    status: str
    resumes_parsed: int
    candidates_saved: int
    errors: List[str] = []


@router.post("/parse/hh/resumes", response_model=ParseHHResumesResponse)
async def parse_hh_resumes(request: ParseHHResumesRequest):
    """Парсинг резюме HH и сохранение кандидатов (per_page ≤ 20)."""
    from app.parsers import HHResumeParser

    errors = []
    resumes_parsed = 0
    candidates_saved = 0

    try:
        async with HHResumeParser() as parser:
            all_resumes = []

            for page in range(request.max_pages):
                parsed_resumes = await parser.parse_list(
                    query=request.query,
                    area=request.area,
                    page=page,
                    per_page=min(request.per_page, 20),
                    search_field=request.search_field,
                    logic=request.logic
                )
                all_resumes.extend(parsed_resumes)

                if len(parsed_resumes) < request.per_page:
                    break

            resumes_parsed = len(all_resumes)

            with DatabaseService() as db:
                for pr in all_resumes:
                    try:
                        db.create_candidate_from_parsed(pr)
                        candidates_saved += 1
                    except Exception as e:
                        pos = pr.position_title or pr.external_id
                        errors.append(f"Ошибка сохранения {pos}: {str(e)}")

        return ParseHHResumesResponse(
            status="success" if candidates_saved > 0 else "partial",
            resumes_parsed=resumes_parsed,
            candidates_saved=candidates_saved,
            errors=errors
        )

    except Exception as e:
        return ParseHHResumesResponse(
            status="error",
            resumes_parsed=resumes_parsed,
            candidates_saved=candidates_saved,
            errors=[str(e)]
        )


class ParseHHResumeByUrlRequest(BaseModel):
    url: str


@router.post("/parse/hh/resume")
async def parse_hh_resume_by_url(request: ParseHHResumeByUrlRequest):
    """Одно резюме по URL → БД."""
    from app.parsers import HHResumeParser

    try:
        async with HHResumeParser() as parser:
            parsed_resume = await parser.parse_item(request.url)

            if not parsed_resume:
                raise HTTPException(status_code=400, detail="Не удалось распарсить резюме")

            with DatabaseService() as db:
                candidate = db.create_candidate_from_parsed(parsed_resume)
                return {
                    "status": "success",
                    "candidate_id": candidate.id,
                    "position": parsed_resume.position_title,
                    "skills_count": len(parsed_resume.skills_raw),
                    "experience_months": parsed_resume.total_experience_months
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MatchVacancyRequest(BaseModel):
    vacancy_id: int
    min_score: float = 0.3
    limit: int = 20
    embedding_prefilter_top: Optional[int] = Field(
        None,
        ge=0,
        le=2000,
        description="Предфильтр по эмбеддингу резюме к вакансии перед полным скором. "
        "None — значение из MATCH_EMBEDDING_PREFILTER_TOP; 0 — отключить (весь пул).",
    )


@router.post("/match/vacancy")
async def match_candidates_for_vacancy(request: MatchVacancyRequest):
    """Ранжирование кандидатов по вакансии, сохранение матчей в БД."""
    with DatabaseService() as db:
        vacancy = db.get_vacancy_by_id(request.vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=404, detail="Vacancy not found")

        vacancy_response = db.vacancy_to_response(vacancy)
        vacancy_response = merge_skills_from_vacancy_description(
            vacancy_response, skill_extractor, db
        )

        candidates = db.get_all_candidates(limit=500)
        if not candidates:
            return {
                "vacancy": vacancy_response,
                "candidates": [],
                "total_candidates": 0
            }

        candidate_responses = [db.candidate_to_response(c) for c in candidates]

        embedding_service = EmbeddingService()
        matching_service = MatchingService(
            embedding_service=embedding_service,
            skills_service=skills_service
        )
        ranker = CandidateRanker(
            matching_service=matching_service,
            embedding_service=embedding_service
        )

        matches = ranker.rank_candidates(
            vacancy=vacancy_response,
            candidates=candidate_responses,
            top_k=request.limit,
            min_score=request.min_score,
            embedding_prefilter_top=request.embedding_prefilter_top,
        )

        for match in matches:
            db.save_match_result(
                candidate_id=match.candidate_id,
                vacancy_id=request.vacancy_id,
                match=match
            )

        results = []
        for i, match in enumerate(matches, 1):
            candidate = next(
                (c for c in candidate_responses if c.id == match.candidate_id),
                None
            )
            if candidate:
                results.append({
                    "rank": i,
                    "candidate": candidate.model_dump(),
                    "match": match.model_dump()
                })

        return {
            "vacancy": vacancy_response.model_dump(),
            "candidates": results,
            "total_candidates": len(results)
        }


@router.get("/match/vacancy/{vacancy_id}/results")
async def get_vacancy_match_results(
    vacancy_id: int,
    min_score: float = Query(0.0, ge=0, le=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Сохранённые матчи по вакансии."""
    with DatabaseService() as db:
        vacancy = db.get_vacancy_by_id(vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=404, detail="Vacancy not found")

        results = db.get_matches_for_vacancy(
            vacancy_id=vacancy_id,
            min_score=min_score,
            limit=limit
        )

        return {
            "vacancy": db.vacancy_to_response(vacancy).model_dump(),
            "candidates": results,
            "total": len(results)
        }


class SkillNormalizationRequest(BaseModel):
    skills: List[str]


class SkillNormalizationResponse(BaseModel):
    normalized: List[dict]
    specialization: Optional[str] = None


@router.post("/skills/normalize", response_model=SkillNormalizationResponse)
async def normalize_skills(request: SkillNormalizationRequest):
    """Нормализация списка строк навыков."""
    results = skills_service.normalizer.normalize_list(request.skills)

    normalized = []
    valid_skills = []

    for original, normalized_name in results:
        if normalized_name:
            valid_skills.append(normalized_name)
            groups = skills_service.normalizer.get_skill_groups(normalized_name)
            normalized.append({
                "original": original,
                "normalized": normalized_name,
                "groups": groups,
                "found": True
            })
        else:
            normalized.append({
                "original": original,
                "normalized": None,
                "groups": [],
                "found": False
            })

    specialization = skills_service.detect_specialization(valid_skills)

    return SkillNormalizationResponse(
        normalized=normalized,
        specialization=specialization.value if specialization else None
    )


class SkillExtractionRequest(BaseModel):
    text: str
    context: Optional[str] = None
    include_ner_spans: bool = False


@router.post("/skills/extract", response_model=SkillExtractionResult)
async def extract_skills(request: SkillExtractionRequest):
    """Извлечение навыков из текста; при include_ner_spans — сырые NER-спаны."""
    return skill_extractor.extract_skills(
        text=request.text,
        context=request.context,
        include_ner_spans=request.include_ner_spans,
    )


class NerExtractRequest(BaseModel):
    text: str


@router.post("/skills/ner", response_model=List[NerSpan])
async def extract_skill_ner_entities(request: NerExtractRequest):
    """NER по словарю (label SKILL)."""
    from app.services.ner_service import extract_dictionary_skill_spans

    raw = extract_dictionary_skill_spans(request.text, skills_service.normalizer)
    return [NerSpan(text=t, label=lab, start=s, end=e) for t, s, e, lab in raw]


@router.get("/skills/groups")
async def get_skill_groups():
    """Все группы навыков из словаря."""
    return skills_service.get_all_groups()


@router.get("/skills/coverage")
async def calculate_coverage(
    candidate_skills: List[str] = Query(..., description="Навыки кандидата"),
    required_skills: List[str] = Query(..., description="Обязательные навыки"),
    optional_skills: List[str] = Query(default=[], description="Опциональные навыки")
):
    """Покрытие навыков (см. ``SkillsService.calculate_skills_coverage``)."""
    return skills_service.calculate_skills_coverage(
        candidate_skills=candidate_skills,
        required_skills=required_skills,
        optional_skills=optional_skills
    )


class VacancyAnalysisRequest(BaseModel):
    title: str
    description: str
    requirements: Optional[str] = None


class VacancyAnalysisResponse(BaseModel):
    skills: SkillExtractionResult
    parsed: ParsedVacancy


@router.post("/vacancies/analyze", response_model=VacancyAnalysisResponse)
async def analyze_vacancy(request: VacancyAnalysisRequest):
    """Разбор текста вакансии без сохранения в БД."""
    from app.models.schemas import SourceTypeEnum

    skills = skill_extractor.extract_from_vacancy(
        title=request.title,
        description=request.description,
        requirements=request.requirements
    )

    parsed = ParsedVacancy(
        source=SourceTypeEnum.MANUAL,
        external_id="manual_" + str(hash(request.title))[:8],
        title=request.title,
        company="Not specified",
        description=request.description,
        skills_raw=[s.normalized_name for s in skills.skills]
    )

    return VacancyAnalysisResponse(
        skills=skills,
        parsed=parsed
    )


class MatchRequest(BaseModel):
    vacancy_title: str
    vacancy_description: str
    vacancy_skills: List[str]
    candidate_position: str
    candidate_skills: List[str]
    candidate_experience_months: Optional[int] = None
    candidate_about: Optional[str] = None


class SimpleMatchResponse(BaseModel):
    total_score: float
    skills_score: float
    embedding_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    extra_skills: List[str]


@router.post("/match/simple", response_model=SimpleMatchResponse)
async def simple_match(request: MatchRequest):
    """Упрощённый скор без БД (0.6 навыки + 0.4 эмбеддинг)."""
    embedding_service = EmbeddingService()

    coverage = skills_service.calculate_skills_coverage(
        candidate_skills=request.candidate_skills,
        required_skills=request.vacancy_skills,
        optional_skills=[]
    )

    vacancy_embedding = embedding_service.create_vacancy_embedding(
        title=request.vacancy_title,
        description=request.vacancy_description,
        skills=request.vacancy_skills
    )

    candidate_embedding = embedding_service.create_resume_embedding(
        position_title=request.candidate_position,
        skills=request.candidate_skills,
        about=request.candidate_about
    )

    embedding_score = float(embedding_service.cosine_similarity(
        vacancy_embedding,
        candidate_embedding
    ))

    total_score = 0.6 * coverage["total_score"] + 0.4 * max(0, embedding_score)

    return SimpleMatchResponse(
        total_score=round(total_score, 4),
        skills_score=round(coverage["total_score"], 4),
        embedding_score=round(embedding_score, 4),
        matched_skills=coverage["matched_required"],
        missing_skills=coverage["missing_required"],
        extra_skills=coverage["extra_skills"]
    )


class EmbeddingRequest(BaseModel):
    texts: List[str]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int


@router.post("/embeddings/encode", response_model=EmbeddingResponse)
async def encode_texts(request: EmbeddingRequest):
    """Батч-эмбеддинги для списка строк."""
    embedding_service = EmbeddingService()
    embeddings = embedding_service.encode(request.texts)

    return EmbeddingResponse(
        embeddings=[emb.tolist() for emb in embeddings],
        dimension=embedding_service.dimension
    )


class SimilarityRequest(BaseModel):
    query: str
    candidates: List[str]
    top_k: int = 5


class SimilarityResponse(BaseModel):
    results: List[dict]


@router.post("/embeddings/similarity", response_model=SimilarityResponse)
async def find_similar(request: SimilarityRequest):
    """Top-k по косинусу среди строк-кандидатов."""
    embedding_service = EmbeddingService()

    results = embedding_service.find_most_similar(
        query=request.query,
        candidates=request.candidates,
        top_k=request.top_k
    )

    for r in results:
        r["text"] = request.candidates[r["index"]]

    return SimilarityResponse(results=results)


@router.get("/health")
async def health_check():
    """Health: БД и ключевые сервисы."""
    with DatabaseService() as db:
        stats = db.get_statistics()

    return {
        "status": "healthy",
        "database": stats,
        "services": {
            "skills_service": "ok",
            "skill_extractor": "ok"
        }
    }
