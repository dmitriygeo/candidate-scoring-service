"""Матчинг кандидатов с вакансиями: скоры, ранжирование, детализация."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np

from loguru import logger

from config import settings

from app.models.schemas import (
    CandidateResponse,
    VacancyResponse,
    MatchResult,
    MatchScoreDetails,
    WorkFormatEnum,
)
from app.services.embeddings import EmbeddingService
from app.services.skills import SkillsService
from app.services.hybrid_ranker import get_hybrid_ranker
from app.services.hybrid_ranker_text import build_resume_text, build_vacancy_text


@dataclass
class MatchWeights:
    """Веса компонентов итогового скора."""
    skills: float = 0.35
    experience: float = 0.20
    education: float = 0.10
    salary: float = 0.10
    location: float = 0.10
    embedding: float = 0.15

    def normalize(self):
        """Нормализовать веса так, чтобы сумма была 1."""
        total = self.skills + self.experience + self.education + self.salary + self.location + self.embedding
        if total > 0:
            self.skills /= total
            self.experience /= total
            self.education /= total
            self.salary /= total
            self.location /= total
            self.embedding /= total


class MatchingService:
    """Взвешенный скор по навыкам, опыту, образованию, зарплате, локации и эмбеддингам."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        skills_service: Optional[SkillsService] = None,
        weights: Optional[MatchWeights] = None
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.skills_service = skills_service or SkillsService()
        self.weights = weights or MatchWeights()
        self.weights.normalize()

    def calculate_match(
        self,
        candidate: CandidateResponse,
        vacancy: VacancyResponse,
        candidate_embedding: Optional[np.ndarray] = None,
        vacancy_embedding: Optional[np.ndarray] = None
    ) -> MatchResult:
        """Скор матчинга для пары кандидат–вакансия; эмбеддинги можно передать заранее."""
        skills_result = self._calculate_skills_score(candidate, vacancy)
        experience_score = self._calculate_experience_score(candidate, vacancy)
        education_score = self._calculate_education_score(candidate)
        salary_score = self._calculate_salary_score(candidate, vacancy)
        location_score = self._calculate_location_score(candidate, vacancy)

        embedding_score = 0.0
        if candidate_embedding is not None and vacancy_embedding is not None:
            embedding_score = float(np.dot(candidate_embedding, vacancy_embedding))
            embedding_score = max(0.0, embedding_score)
        elif vacancy.description:
            embedding_score = self._calculate_embedding_score(candidate, vacancy)

        total_score = (
            self.weights.skills * skills_result["total_score"] +
            self.weights.experience * experience_score +
            self.weights.education * education_score +
            self.weights.salary * salary_score +
            self.weights.location * location_score +
            self.weights.embedding * embedding_score
        )

        details = MatchScoreDetails(
            matched_skills=skills_result["matched_required"] + skills_result.get("matched_optional", []),
            missing_required_skills=skills_result["missing_required"],
            missing_optional_skills=skills_result.get("missing_optional", []),
            extra_skills=skills_result.get("extra_skills", []),
            experience_match={
                "candidate_months": candidate.total_experience_months,
                "required_months": vacancy.experience_from,
                "score": experience_score
            },
            salary_match={
                "candidate_min": candidate.desired_salary_min,
                "candidate_max": candidate.desired_salary_max,
                "vacancy_min": vacancy.salary_from,
                "vacancy_max": vacancy.salary_to,
                "score": salary_score
            },
            location_match={
                "candidate_city": candidate.city,
                "vacancy_city": vacancy.city,
                "candidate_format": candidate.work_format.value if candidate.work_format else None,
                "vacancy_format": vacancy.work_format.value if vacancy.work_format else None,
                "score": location_score
            }
        )

        return MatchResult(
            candidate_id=candidate.id,
            vacancy_id=vacancy.id,
            total_score=round(total_score, 4),
            skills_score=round(skills_result["total_score"], 4),
            experience_score=round(experience_score, 4),
            education_score=round(education_score, 4),
            salary_score=round(salary_score, 4),
            location_score=round(location_score, 4),
            embedding_score=round(embedding_score, 4),
            score_details=details
        )

    def _calculate_skills_score(
        self,
        candidate: CandidateResponse,
        vacancy: VacancyResponse
    ) -> Dict:
        """Покрытие навыков вакансии навыками кандидата (все требования считаются обязательными)."""
        candidate_skills = [s.skill_name for s in candidate.skills]
        required_skills = [s.skill_name for s in vacancy.skills if s.skill_name]
        optional_skills: List[str] = []

        return self.skills_service.calculate_skills_coverage(
            candidate_skills,
            required_skills,
            optional_skills
        )

    def _calculate_experience_score(
        self,
        candidate: CandidateResponse,
        vacancy: VacancyResponse
    ) -> float:
        """Соответствие стажа требованиям вакансии (в т.ч. переквалификация)."""
        candidate_exp = candidate.total_experience_months or 0
        required_exp = vacancy.experience_from or 0
        max_exp = vacancy.experience_to

        if required_exp == 0:
            return min(1.0, candidate_exp / 36)

        if candidate_exp >= required_exp:
            if max_exp and candidate_exp > max_exp:
                overqualification = (candidate_exp - max_exp) / max_exp
                return max(0.7, 1.0 - overqualification * 0.3)
            return 1.0
        return candidate_exp / required_exp

    def _calculate_education_score(
        self,
        candidate: CandidateResponse
    ) -> float:
        """Оценка образования по степени и рейтингу вуза."""
        if not candidate.education:
            return 0.3

        best_score = 0.3

        for edu in candidate.education:
            score = 0.5

            degree_bonus = {
                "bachelor": 0.2,
                "master": 0.3,
                "phd": 0.4,
                "specialist": 0.25,
            }
            if edu.degree:
                score += degree_bonus.get(edu.degree.lower(), 0.1)

            if edu.university_rating:
                score += min(0.2, edu.university_rating / 500)

            best_score = max(best_score, min(1.0, score))

        return best_score

    def _calculate_salary_score(
        self,
        candidate: CandidateResponse,
        vacancy: VacancyResponse
    ) -> float:
        """Согласование диапазонов зарплат кандидата и вакансии."""
        if not vacancy.salary_from and not vacancy.salary_to:
            return 0.5

        if not candidate.desired_salary_min and not candidate.desired_salary_max:
            return 0.5

        vacancy_min = vacancy.salary_from or 0
        vacancy_max = vacancy.salary_to or vacancy_min * 1.5

        candidate_min = candidate.desired_salary_min or 0
        candidate_max = candidate.desired_salary_max or candidate_min * 1.3

        if candidate_min <= vacancy_max and candidate_max >= vacancy_min:
            overlap_min = max(candidate_min, vacancy_min)
            overlap_max = min(candidate_max, vacancy_max)

            vacancy_range = vacancy_max - vacancy_min if vacancy_max > vacancy_min else vacancy_max
            overlap = overlap_max - overlap_min

            return min(1.0, 0.5 + 0.5 * (overlap / vacancy_range if vacancy_range > 0 else 1))

        if candidate_min > vacancy_max:
            gap = (candidate_min - vacancy_max) / vacancy_max if vacancy_max > 0 else 1
            return max(0.0, 0.5 - gap)

        return 0.8

    def _calculate_location_score(
        self,
        candidate: CandidateResponse,
        vacancy: VacancyResponse
    ) -> float:
        """Локация и формат работы."""
        score = 0.5

        if vacancy.work_format == WorkFormatEnum.REMOTE:
            score = 1.0
        elif candidate.work_format == vacancy.work_format:
            score += 0.3
        elif candidate.work_format == WorkFormatEnum.HYBRID:
            score += 0.2

        if vacancy.city and candidate.city:
            if vacancy.city.lower() == candidate.city.lower():
                score += 0.2
            elif candidate.relocation_ready:
                score += 0.1
        elif not vacancy.city:
            score += 0.1

        return min(1.0, score)

    def _calculate_embedding_score(
        self,
        candidate: CandidateResponse,
        vacancy: VacancyResponse
    ) -> float:
        """Косинусная близость эмбеддингов резюме и вакансии."""
        try:
            candidate_skills = [s.skill_name for s in candidate.skills]
            candidate_exp = "\n".join([
                f"{exp.position} в {exp.company}"
                for exp in candidate.work_experience[:3]
            ]) if candidate.work_experience else ""

            candidate_embedding = self.embedding_service.create_resume_embedding(
                position_title=candidate.position_title,
                skills=candidate_skills,
                experience_summary=candidate_exp,
                about=candidate.about
            )

            vacancy_skills = [s.skill_name for s in vacancy.skills]
            vacancy_embedding = self.embedding_service.create_vacancy_embedding(
                title=vacancy.title,
                description=vacancy.description,
                skills=vacancy_skills,
                company=vacancy.company
            )

            similarity = self.embedding_service.cosine_similarity(
                candidate_embedding,
                vacancy_embedding
            )

            return max(0.0, similarity)

        except Exception as e:
            logger.warning(f"Ошибка расчёта embedding score: {e}")
            return 0.0


class CandidateRanker:
    """Ранжирование кандидатов по вакансии (эвристика + опциональный гибрид)."""

    def __init__(
        self,
        matching_service: Optional[MatchingService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        self.matching_service = matching_service or MatchingService()
        self.embedding_service = embedding_service or EmbeddingService()

    def rank_candidates(
        self,
        vacancy: VacancyResponse,
        candidates: List[CandidateResponse],
        top_k: Optional[int] = None,
        min_score: float = 0.0,
        embedding_prefilter_top: Optional[int] = None,
    ) -> List[MatchResult]:
        """Ранжирование по скору; ``embedding_prefilter_top``: None — из настроек, 0 — без предфильтра."""
        pref = (
            settings.MATCH_EMBEDDING_PREFILTER_TOP
            if embedding_prefilter_top is None
            else embedding_prefilter_top
        )
        pref = max(0, int(pref))
        matches = self.collect_matches(
            vacancy,
            candidates,
            min_score=0.0,
            embedding_prefilter_top=pref,
        )

        hybrid = get_hybrid_ranker()
        if hybrid is not None and hybrid.is_ready:
            cand_by_id = {c.id: c for c in candidates}
            vacancy_text = build_vacancy_text(vacancy)
            resume_texts = []
            for m in matches:
                c = cand_by_id.get(m.candidate_id)
                resume_texts.append(build_resume_text(c) if c else "")
            if resume_texts:
                v_dup = [vacancy_text] * len(resume_texts)
                scores = hybrid.score_batch(resume_texts, v_dup)
                for m, s in zip(matches, scores):
                    if m.score_details is not None:
                        m.score_details.heuristic_total_score = m.total_score
                        m.score_details.hybrid_ranker_score = round(float(s), 4)
                    m.total_score = round(float(s), 4)

        matches = [m for m in matches if m.total_score >= min_score]
        matches.sort(key=lambda m: m.total_score, reverse=True)

        for rank, match in enumerate(matches, 1):
            match.rank = rank

        if top_k:
            matches = matches[:top_k]

        return matches

    def collect_matches(
        self,
        vacancy: VacancyResponse,
        candidates: List[CandidateResponse],
        min_score: float = 0.0,
        embedding_prefilter_top: int = 0,
    ) -> List[MatchResult]:
        """Список ``MatchResult`` без сортировки по top_k; батч-эмбеддинги и опциональный предфильтр по косинусу."""
        if not candidates:
            return []

        vacancy_skills = [s.skill_name for s in vacancy.skills]
        vacancy_embedding = self.embedding_service.create_vacancy_embedding(
            title=vacancy.title,
            description=vacancy.description,
            skills=vacancy_skills,
            company=vacancy.company,
        )

        texts: List[str] = []
        for candidate in candidates:
            candidate_skills = [s.skill_name for s in candidate.skills]
            candidate_exp = "\n".join(
                [
                    f"{exp.position} в {exp.company}"
                    for exp in candidate.work_experience[:3]
                ]
            ) if candidate.work_experience else ""
            texts.append(
                self.embedding_service.build_resume_embedding_text(
                    position_title=candidate.position_title,
                    skills=candidate_skills,
                    experience_summary=candidate_exp,
                    about=candidate.about,
                )
            )

        cand_matrix = self.embedding_service.encode(texts)
        cand_matrix = np.asarray(cand_matrix, dtype=np.float64)

        if (
            embedding_prefilter_top > 0
            and len(candidates) > embedding_prefilter_top
        ):
            sims = self.embedding_service.cosine_similarity_batch(
                vacancy_embedding, cand_matrix
            )
            top_idx = np.argsort(sims)[::-1][:embedding_prefilter_top]
            candidates = [candidates[int(i)] for i in top_idx]
            cand_matrix = cand_matrix[top_idx]

        matches: List[MatchResult] = []
        for candidate, row in zip(candidates, cand_matrix):
            candidate_embedding = np.asarray(row).reshape(-1)

            match = self.matching_service.calculate_match(
                candidate=candidate,
                vacancy=vacancy,
                candidate_embedding=candidate_embedding,
                vacancy_embedding=vacancy_embedding,
            )
            if match.total_score >= min_score:
                matches.append(match)
        return matches

    def quick_rank_by_embedding(
        self,
        vacancy: VacancyResponse,
        candidate_embeddings: Dict[int, np.ndarray],
        top_k: int = 100
    ) -> List[Dict[str, Any]]:
        """Только эмбеддинг-косинус к вакансии, без полного скора."""
        if not candidate_embeddings:
            return []

        vacancy_skills = [s.skill_name for s in vacancy.skills]
        vacancy_embedding = self.embedding_service.create_vacancy_embedding(
            title=vacancy.title,
            description=vacancy.description,
            skills=vacancy_skills,
            company=vacancy.company
        )

        ids = list(candidate_embeddings.keys())
        embeddings = np.array([candidate_embeddings[id_] for id_ in ids])

        similarities = self.embedding_service.cosine_similarity_batch(
            vacancy_embedding,
            embeddings
        )

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for rank, idx in enumerate(top_indices, 1):
            results.append({
                "candidate_id": ids[idx],
                "embedding_similarity": float(similarities[idx]),
                "rank": rank
            })

        return results
