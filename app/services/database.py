"""Доступ к БД: кандидаты, вакансии, навыки, матчинг."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from app.models.database import (
    Candidate, Vacancy, Skill, SkillGroup,
    CandidateSkill, VacancySkill, Education, WorkExperience,
    CandidateVacancyMatch
)
from app.models.schemas import (
    CandidateResponse, VacancyResponse, MatchResult,
    CandidateSkillSchema, VacancySkillSchema,
    EducationSchema, WorkExperienceSchema, ParsedVacancy, ParsedResume
)
from config import resolved_sync_database_url



engine = create_engine(resolved_sync_database_url(), echo=False)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    """Получить сессию БД"""
    return SessionLocal()


class DatabaseService:
    """Сессия и CRUD для доменных сущностей."""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._own_session = session is None
    
    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_session()
        return self._session
    
    def close(self):
        if self._own_session and self._session:
            self._session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    

    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Получить навык по имени"""
        return self.session.query(Skill).filter(
            (Skill.name == name) | (Skill.normalized_name == name.lower())
        ).first()
    
    def get_or_create_skill(self, name: str) -> Skill:
        """Получить или создать навык"""
        skill = self.get_skill_by_name(name)
        if not skill:
            skill = Skill(
                name=name,
                normalized_name=name.lower().replace(" ", "_"),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.session.add(skill)
            self.session.flush()
        return skill
    
    def get_all_skills(self) -> List[Skill]:
        """Получить все навыки"""
        return self.session.query(Skill).all()
    

    
    def get_vacancy_by_id(self, vacancy_id: int) -> Optional[Vacancy]:
        """Получить вакансию по ID"""
        return self.session.query(Vacancy).filter_by(id=vacancy_id).first()
    
    def get_vacancy_by_external_id(self, source: str, external_id: str) -> Optional[Vacancy]:
        """Получить вакансию по внешнему ID"""
        return self.session.query(Vacancy).filter_by(
            source=source,
            external_id=external_id
        ).first()
    
    def get_all_vacancies(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: bool = True
    ) -> List[Vacancy]:
        """Получить список вакансий"""
        query = self.session.query(Vacancy)
        if is_active:
            query = query.filter_by(is_active=True)
        return query.offset(offset).limit(limit).all()
    
    def persist_vacancy_skills_from_description(
        self,
        vacancy_id: int,
        skill_extractor: Optional[Any] = None,
    ) -> int:
        """Добавляет навыки из текста вакансии в ``vacancy_skills`` без дубликатов ``skill_id``."""
        from app.services.skill_extractor import SkillExtractor
        from app.services.vacancy_match_skills import merge_skills_from_vacancy_description

        vac = self.session.query(Vacancy).filter_by(id=vacancy_id).first()
        if not vac:
            return 0
        ext = skill_extractor or SkillExtractor()
        vr = self.vacancy_to_response(vac)
        merged = merge_skills_from_vacancy_description(vr, ext, self)
        existing = {
            vs.skill_id
            for vs in self.session.query(VacancySkill).filter_by(vacancy_id=vacancy_id).all()
        }
        added = 0
        for s in merged.skills:
            if s.skill_id in existing:
                continue
            existing.add(s.skill_id)
            self.session.add(
                VacancySkill(
                    vacancy_id=vacancy_id,
                    skill_id=s.skill_id,
                    is_required=True,
                )
            )
            added += 1
        if added:
            self.session.flush()
            vac.updated_at = datetime.now()
            logger.info(
                "Вакансия {}: в карточку добавлено {} навыков из описания/заголовка",
                vacancy_id,
                added,
            )
        return added
    
    def create_vacancy_from_parsed(self, parsed: ParsedVacancy) -> Vacancy:
        """Создать вакансию из распарсенных данных"""

        existing = self.get_vacancy_by_external_id(
            parsed.source.value,
            parsed.external_id
        )
        if existing:
            return existing
        
        vacancy = Vacancy(
            title=parsed.title,
            description=parsed.description,
            company=parsed.company,
            salary_from=parsed.salary_from,
            salary_to=parsed.salary_to,
            salary_currency=parsed.salary_currency,
            salary_gross=parsed.salary_gross,
            experience_from=parsed.experience_from,
            experience_to=parsed.experience_to,
            city=parsed.city,
            work_format=parsed.work_format.value if parsed.work_format else None,
            employment_type=parsed.employment_type.value if parsed.employment_type else None,
            source=parsed.source.value,
            external_id=parsed.external_id,
            source_url=parsed.source_url,
            is_active=True,
            published_at=parsed.published_at,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.session.add(vacancy)
        self.session.flush()
        

        for skill_name in parsed.skills_raw:
            skill = self.get_or_create_skill(skill_name)
            vacancy_skill = VacancySkill(
                vacancy_id=vacancy.id,
                skill_id=skill.id,
                is_required=True
            )
            self.session.add(vacancy_skill)
        
        self.session.flush()
        self.persist_vacancy_skills_from_description(vacancy.id)
        self.session.commit()
        return vacancy
    
    def vacancy_to_response(self, vacancy: Vacancy) -> VacancyResponse:
        """Преобразовать Vacancy в VacancyResponse"""
        skills = []
        for vs in self.session.query(VacancySkill).filter_by(vacancy_id=vacancy.id).all():
            skill = self.session.query(Skill).filter_by(id=vs.skill_id).first()
            if skill:
                skills.append(VacancySkillSchema(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    is_required=vs.is_required,
                    required_level=vs.required_level,
                    required_experience_months=vs.required_experience_months
                ))
        
        return VacancyResponse(
            id=vacancy.id,
            title=vacancy.title,
            description=vacancy.description,
            company=vacancy.company,
            salary_from=vacancy.salary_from,
            salary_to=vacancy.salary_to,
            salary_currency=vacancy.salary_currency,
            salary_gross=vacancy.salary_gross,
            experience_from=vacancy.experience_from,
            experience_to=vacancy.experience_to,
            city=vacancy.city,
            work_format=vacancy.work_format,
            employment_type=vacancy.employment_type,
            specialization_group=vacancy.specialization_group,
            skills=skills,
            source=vacancy.source,
            external_id=vacancy.external_id,
            source_url=vacancy.source_url,
            is_active=vacancy.is_active,
            published_at=vacancy.published_at,
            created_at=vacancy.created_at,
            updated_at=vacancy.updated_at
        )
    

    
    def get_candidate_by_id(self, candidate_id: int) -> Optional[Candidate]:
        """Получить кандидата по ID"""
        return self.session.query(Candidate).filter_by(id=candidate_id).first()
    
    def get_candidate_by_external_id(self, source: str, external_id: str) -> Optional[Candidate]:
        """Получить кандидата по внешнему ID профиля"""
        from app.models.database import CandidateProfile
        profile = self.session.query(CandidateProfile).filter_by(
            source=source,
            external_id=external_id
        ).first()
        if profile:
            return self.get_candidate_by_id(profile.candidate_id)
        return None
    
    def create_candidate_from_parsed(self, parsed: ParsedResume) -> Candidate:
        """Создать кандидата из распарсенного резюме."""
        from app.models.database import CandidateProfile, CandidateSkill, Education as EducationModel, WorkExperience

        existing = self.get_candidate_by_external_id(
            parsed.source.value,
            parsed.external_id
        )
        if existing:
            return existing

        candidate = Candidate(
            first_name=parsed.first_name,
            last_name=parsed.last_name,
            middle_name=parsed.middle_name,
            email=parsed.email,
            phone=parsed.phone,
            birth_date=parsed.birth_date,
            city=parsed.city,
            country="Россия",
            relocation_ready=False,
            desired_salary_min=parsed.desired_salary,
            desired_salary_max=parsed.desired_salary,
            salary_currency=parsed.salary_currency,
            work_format=parsed.work_format.value if parsed.work_format else None,
            position_title=parsed.position_title,
            total_experience_months=parsed.total_experience_months,
            is_active_search=True,
            about=parsed.about,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.session.add(candidate)
        self.session.flush()

        raw_data_str = json.dumps(parsed.raw_data, ensure_ascii=False) if parsed.raw_data else None
        profile = CandidateProfile(
            candidate_id=candidate.id,
            source=parsed.source.value,
            external_id=parsed.external_id,
            profile_url=parsed.profile_url,
            raw_data=raw_data_str,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.session.add(profile)

        for skill_name in parsed.skills_raw:
            skill = self.get_or_create_skill(skill_name)
            candidate_skill = CandidateSkill(
                candidate_id=candidate.id,
                skill_id=skill.id,
                level="intermediate",
                is_verified=False
            )
            self.session.add(candidate_skill)

        for edu in parsed.education:
            education = EducationModel(
                candidate_id=candidate.id,
                institution=edu.institution,
                faculty=edu.faculty,
                specialization=edu.specialization,
                degree=edu.degree,
                start_year=edu.start_year,
                end_year=edu.end_year
            )
            self.session.add(education)

        for exp in parsed.work_experience:
            duration_months = getattr(exp, 'duration_months', None)

            if duration_months is None:
                if exp.start_date and exp.end_date:
                    delta = exp.end_date - exp.start_date
                    duration_months = int(delta.days / 30)
                elif exp.start_date and exp.is_current:
                    delta = datetime.now() - exp.start_date
                    duration_months = int(delta.days / 30)
            
            work_exp = WorkExperience(
                candidate_id=candidate.id,
                company=exp.company,
                position=exp.position,
                description=exp.description,
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                duration_months=duration_months
            )
            self.session.add(work_exp)
        
        self.session.commit()
        return candidate
    
    def get_all_candidates(
        self,
        limit: int = 100,
        offset: int = 0,
        specialization: Optional[str] = None
    ) -> List[Candidate]:
        """Получить список кандидатов"""
        query = self.session.query(Candidate)
        if specialization:
            query = query.filter_by(specialization_group=specialization)
        return query.offset(offset).limit(limit).all()
    
    def candidate_to_response(self, candidate: Candidate) -> CandidateResponse:
        """Преобразовать Candidate в CandidateResponse."""
        skills = []
        for cs in self.session.query(CandidateSkill).filter_by(candidate_id=candidate.id).all():
            skill = self.session.query(Skill).filter_by(id=cs.skill_id).first()
            if skill:
                skills.append(CandidateSkillSchema(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    level=cs.level,
                    experience_months=cs.experience_months,
                    last_used=cs.last_used,
                    is_verified=cs.is_verified,
                    verification_source=cs.verification_source
                ))

        education = []
        for edu in self.session.query(Education).filter_by(candidate_id=candidate.id).all():
            education.append(EducationSchema(
                id=edu.id,
                institution=edu.institution,
                faculty=edu.faculty,
                specialization=edu.specialization,
                degree=edu.degree,
                start_year=edu.start_year,
                end_year=edu.end_year,
                university_rating=edu.university_rating,
                average_ege_score=edu.average_ege_score
            ))

        work_experience = []
        for exp in self.session.query(WorkExperience).filter_by(candidate_id=candidate.id).all():
            work_experience.append(WorkExperienceSchema(
                id=exp.id,
                company=exp.company,
                position=exp.position,
                description=exp.description,
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                duration_months=exp.duration_months,
                company_rating=exp.company_rating
            ))

        from app.models.database import CandidateProfile
        from app.models.schemas import CandidateProfileSchema
        
        profiles = []
        for prof in self.session.query(CandidateProfile).filter_by(candidate_id=candidate.id).all():
            profiles.append(CandidateProfileSchema(
                source=prof.source,
                external_id=prof.external_id,
                profile_url=prof.profile_url,
                resume_url=prof.resume_url
            ))
        
        return CandidateResponse(
            id=candidate.id,
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            middle_name=candidate.middle_name,
            email=candidate.email,
            phone=candidate.phone,
            birth_date=candidate.birth_date,
            city=candidate.city,
            country=candidate.country,
            relocation_ready=candidate.relocation_ready,
            desired_salary_min=candidate.desired_salary_min,
            desired_salary_max=candidate.desired_salary_max,
            salary_currency=candidate.salary_currency,
            work_format=candidate.work_format,
            employment_type=candidate.employment_type,
            specialization_group=candidate.specialization_group,
            position_title=candidate.position_title,
            total_experience_months=candidate.total_experience_months,
            is_active_search=candidate.is_active_search,
            current_employer=candidate.current_employer,
            about=candidate.about,
            skills=skills,
            education=education,
            work_experience=work_experience,
            profiles=profiles,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at
        )

    def save_match_result(
        self,
        candidate_id: int,
        vacancy_id: int,
        match: MatchResult
    ) -> CandidateVacancyMatch:
        """Сохранить или обновить результат матчинга."""
        existing = self.session.query(CandidateVacancyMatch).filter_by(
            candidate_id=candidate_id,
            vacancy_id=vacancy_id
        ).first()
        
        if existing:
            existing.total_score = match.total_score
            existing.skills_score = match.skills_score
            existing.experience_score = match.experience_score
            existing.education_score = match.education_score
            existing.salary_score = match.salary_score
            existing.location_score = match.location_score
            existing.embedding_score = match.embedding_score
            existing.github_score = match.github_score
            existing.score_details = json.dumps(match.score_details.model_dump()) if match.score_details else None
            existing.calculated_at = datetime.now()
            self.session.commit()
            return existing

        db_match = CandidateVacancyMatch(
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            total_score=match.total_score,
            skills_score=match.skills_score,
            experience_score=match.experience_score,
            education_score=match.education_score,
            salary_score=match.salary_score,
            location_score=match.location_score,
            embedding_score=match.embedding_score,
            github_score=match.github_score,
            score_details=json.dumps(match.score_details.model_dump()) if match.score_details else None,
            calculated_at=datetime.now()
        )
        self.session.add(db_match)
        self.session.commit()
        return db_match
    
    def get_matches_for_vacancy(
        self,
        vacancy_id: int,
        min_score: float = 0.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Получить кандидатов для вакансии"""
        matches = self.session.query(CandidateVacancyMatch).filter(
            CandidateVacancyMatch.vacancy_id == vacancy_id,
            CandidateVacancyMatch.total_score >= min_score
        ).order_by(
            CandidateVacancyMatch.total_score.desc()
        ).limit(limit).all()
        
        results = []
        for i, m in enumerate(matches, 1):
            candidate = self.get_candidate_by_id(m.candidate_id)
            if candidate:
                details = None
                if m.score_details:
                    try:
                        details = json.loads(m.score_details)
                    except (json.JSONDecodeError, TypeError):
                        details = None
                results.append({
                    "rank": i,
                    "candidate": self.candidate_to_response(candidate),
                    "match": {
                        "candidate_id": m.candidate_id,
                        "vacancy_id": m.vacancy_id,
                        "total_score": m.total_score,
                        "skills_score": m.skills_score,
                        "experience_score": m.experience_score,
                        "education_score": m.education_score,
                        "salary_score": m.salary_score,
                        "location_score": m.location_score,
                        "embedding_score": m.embedding_score,
                        "github_score": m.github_score,
                        "rank": i,
                        "score_details": details,
                    },
                })
        
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику БД"""
        return {
            "candidates_count": self.session.query(func.count(Candidate.id)).scalar(),
            "vacancies_count": self.session.query(func.count(Vacancy.id)).scalar(),
            "skills_count": self.session.query(func.count(Skill.id)).scalar(),
            "skill_groups_count": self.session.query(func.count(SkillGroup.id)).scalar(),
            "matches_count": self.session.query(func.count(CandidateVacancyMatch.id)).scalar(),
        }


