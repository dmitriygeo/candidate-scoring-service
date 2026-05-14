"""Pydantic-схемы API и валидации."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class SpecializationGroupEnum(str, Enum):
    """Группы специализаций"""
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    DATA_SCIENCE = "data_science"
    DATA_ENGINEERING = "data_engineering"
    ML_ENGINEER = "ml_engineer"
    DEVOPS = "devops"
    QA = "qa"
    MOBILE = "mobile"
    SYSTEM_ANALYST = "system_analyst"
    PRODUCT_MANAGER = "product_manager"
    PROJECT_MANAGER = "project_manager"
    OTHER = "other"


class WorkFormatEnum(str, Enum):
    """Формат работы"""
    REMOTE = "remote"
    OFFICE = "office"
    HYBRID = "hybrid"


class EmploymentTypeEnum(str, Enum):
    """Тип занятости"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    PROJECT = "project"
    INTERNSHIP = "internship"


class SkillLevelEnum(str, Enum):
    """Уровень владения навыком"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SourceTypeEnum(str, Enum):
    """Источник данных"""
    HH = "hh"
    SUPERJOB = "superjob"
    HABR_CAREER = "habr_career"
    LINKEDIN = "linkedin"
    GITHUB = "github"
    TELEGRAM = "telegram"
    MANUAL = "manual"
    TRAIN_IT = "train_it"


class SkillBase(BaseModel):
    """Базовая схема навыка"""
    name: str
    aliases: Optional[List[str]] = None
    description: Optional[str] = None


class SkillSchema(SkillBase):
    """Схема навыка с ID"""
    id: int
    normalized_name: str
    groups: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class SkillGroupSchema(BaseModel):
    """Схема группы навыков"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    skills: Optional[List[SkillSchema]] = None
    
    class Config:
        from_attributes = True


class CandidateSkillSchema(BaseModel):
    """Навык кандидата"""
    skill_id: int
    skill_name: str
    level: Optional[SkillLevelEnum] = None
    experience_months: Optional[int] = None
    last_used: Optional[datetime] = None
    is_verified: bool = False
    verification_source: Optional[str] = None
    
    class Config:
        from_attributes = True


class EducationBase(BaseModel):
    """Базовая схема образования"""
    institution: str
    faculty: Optional[str] = None
    specialization: Optional[str] = None
    degree: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class EducationSchema(EducationBase):
    """Схема образования с рейтингом"""
    id: int
    university_rating: Optional[float] = None
    average_ege_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class WorkExperienceBase(BaseModel):
    """Базовая схема опыта работы"""
    company: str
    position: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: bool = False
    duration_months: Optional[int] = None


class WorkExperienceSchema(WorkExperienceBase):
    """Схема опыта работы"""
    id: int
    duration_months: Optional[int] = None
    company_rating: Optional[float] = None
    
    class Config:
        from_attributes = True


class CandidateProfileSchema(BaseModel):
    """Схема профиля кандидата из источника"""
    source: SourceTypeEnum
    external_id: str
    profile_url: Optional[str] = None
    resume_url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class CandidateBase(BaseModel):
    """Базовая схема кандидата"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    birth_date: Optional[datetime] = None
    city: Optional[str] = None
    country: Optional[str] = "Россия"
    relocation_ready: bool = False
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    salary_currency: str = "RUB"
    work_format: Optional[WorkFormatEnum] = None
    employment_type: Optional[EmploymentTypeEnum] = None
    specialization_group: Optional[SpecializationGroupEnum] = None
    position_title: Optional[str] = None
    total_experience_months: Optional[int] = None
    is_active_search: bool = True
    current_employer: Optional[str] = None
    about: Optional[str] = None


class CandidateCreate(CandidateBase):
    """Схема создания кандидата"""
    skills: Optional[List[CandidateSkillSchema]] = None
    education: Optional[List[EducationBase]] = None
    work_experience: Optional[List[WorkExperienceBase]] = None


class CandidateResponse(CandidateBase):
    """Схема ответа с данными кандидата"""
    id: int
    skills: List[CandidateSkillSchema] = []
    education: List[EducationSchema] = []
    work_experience: List[WorkExperienceSchema] = []
    profiles: List[CandidateProfileSchema] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CandidateSearchResult(BaseModel):
    """Результат поиска кандидата"""
    candidate: CandidateResponse
    similarity_score: float = Field(..., ge=0, le=1, description="Косинусная близость")


class VacancySkillSchema(BaseModel):
    """Требуемый навык для вакансии"""
    skill_id: int
    skill_name: str
    is_required: bool = True
    required_level: Optional[SkillLevelEnum] = None
    required_experience_months: Optional[int] = None
    
    class Config:
        from_attributes = True


class VacancyBase(BaseModel):
    """Базовая схема вакансии"""
    title: str
    description: Optional[str] = None
    company: str
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: str = "RUB"
    salary_gross: bool = True
    experience_from: Optional[int] = None
    experience_to: Optional[int] = None
    city: Optional[str] = None
    work_format: Optional[WorkFormatEnum] = None
    employment_type: Optional[EmploymentTypeEnum] = None
    specialization_group: Optional[SpecializationGroupEnum] = None


class VacancyCreate(VacancyBase):
    """Схема создания вакансии"""
    skills: Optional[List[VacancySkillSchema]] = None
    source: Optional[SourceTypeEnum] = SourceTypeEnum.MANUAL
    external_id: Optional[str] = None
    source_url: Optional[str] = None


class VacancyResponse(VacancyBase):
    """Схема ответа с данными вакансии"""
    id: int
    skills: List[VacancySkillSchema] = []
    source: Optional[SourceTypeEnum] = None
    external_id: Optional[str] = None
    source_url: Optional[str] = None
    is_active: bool = True
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MatchScoreDetails(BaseModel):
    """Детальная разбивка скора"""
    matched_skills: List[str] = []
    missing_required_skills: List[str] = []
    missing_optional_skills: List[str] = []
    extra_skills: List[str] = []
    experience_match: Dict[str, Any] = {}
    salary_match: Dict[str, Any] = {}
    location_match: Dict[str, Any] = {}
    hybrid_ranker_score: Optional[float] = Field(
        None, ge=0, le=1, description="Вероятность релевантности по Hybrid HGB"
    )
    heuristic_total_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Предыдущий взвешенный скор до перезаписи total_score гибридом",
    )


class MatchResult(BaseModel):
    """Результат матчинга кандидата с вакансией"""
    candidate_id: int
    vacancy_id: int
    total_score: float = Field(..., ge=0, le=1)

    skills_score: float = Field(0.0, ge=0, le=1)
    experience_score: float = Field(0.0, ge=0, le=1)
    education_score: float = Field(0.0, ge=0, le=1)
    salary_score: float = Field(0.0, ge=0, le=1)
    location_score: float = Field(0.0, ge=0, le=1)
    embedding_score: float = Field(0.0, ge=0, le=1)
    github_score: Optional[float] = Field(None, ge=0, le=1)

    score_details: Optional[MatchScoreDetails] = None

    rank: Optional[int] = None
    
    class Config:
        from_attributes = True


class RankedCandidateResult(BaseModel):
    """Кандидат с рангом в результатах поиска"""
    rank: int
    candidate: CandidateResponse
    match: MatchResult


class VacancyCandidatesResponse(BaseModel):
    """Ответ со списком кандидатов для вакансии"""
    vacancy: VacancyResponse
    candidates: List[RankedCandidateResult]
    total_count: int
    page: int = 1
    page_size: int = 20


class ParsedResume(BaseModel):
    """Результат парсинга резюме"""
    source: SourceTypeEnum
    external_id: str
    profile_url: Optional[str] = None

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[datetime] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    position_title: Optional[str] = None
    about: Optional[str] = None
    desired_salary: Optional[int] = None
    salary_currency: str = "RUB"
    work_format: Optional[WorkFormatEnum] = None

    total_experience_months: Optional[int] = None
    work_experience: List[WorkExperienceBase] = []
    education: List[EducationBase] = []
    skills_raw: List[str] = []
    raw_data: Optional[Dict[str, Any]] = None


class ParsedVacancy(BaseModel):
    """Результат парсинга вакансии"""
    source: SourceTypeEnum
    external_id: str
    source_url: Optional[str] = None
    
    title: str
    company: str
    description: Optional[str] = None
    
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: str = "RUB"
    salary_gross: bool = True
    
    experience_from: Optional[int] = None
    experience_to: Optional[int] = None
    
    city: Optional[str] = None
    work_format: Optional[WorkFormatEnum] = None
    employment_type: Optional[EmploymentTypeEnum] = None

    skills_raw: List[str] = []
    
    published_at: Optional[datetime] = None
    
    raw_data: Optional[Dict[str, Any]] = None


class ExtractedSkill(BaseModel):
    """Извлечённый навык из текста"""
    name: str
    normalized_name: str
    confidence: float = Field(..., ge=0, le=1)
    context: Optional[str] = Field(None, description="Фрагмент текста, где найден навык")
    level_hint: Optional[SkillLevelEnum] = None


class NerSpan(BaseModel):
    """Именованная сущность (NER), найденная словарным EntityRuler по навыкам"""
    text: str
    label: str = "SKILL"
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)


class SkillExtractionResult(BaseModel):
    """Результат извлечения навыков"""
    skills: List[ExtractedSkill]
    specialization_group: Optional[SpecializationGroupEnum] = None
    raw_text: str
    ner_spans: Optional[List[NerSpan]] = Field(
        None, description="Сырые NER-спаны при include_ner_spans в API"
    )


