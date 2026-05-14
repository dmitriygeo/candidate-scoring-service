"""SQLAlchemy-модели: кандидаты, вакансии, навыки, матчинг."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
import enum


class Base(DeclarativeBase):
    """Базовый класс моделей."""
    pass


class SpecializationGroup(enum.Enum):
    """Группы специализаций кандидатов."""
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


class WorkFormat(enum.Enum):
    """Формат работы."""
    REMOTE = "remote"
    OFFICE = "office"
    HYBRID = "hybrid"


class EmploymentType(enum.Enum):
    """Тип занятости."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    PROJECT = "project"
    INTERNSHIP = "internship"


class SkillLevel(enum.Enum):
    """Уровень владения навыком."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SourceType(enum.Enum):
    """Источник данных."""
    HH = "hh"
    SUPERJOB = "superjob"
    HABR_CAREER = "habr_career"
    LINKEDIN = "linkedin"
    GITHUB = "github"
    TELEGRAM = "telegram"
    MANUAL = "manual"
    TRAIN_IT = "train_it"


skill_group_association = Table(
    "skill_group_association",
    Base.metadata,
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("skill_groups.id"), primary_key=True),
)


class SkillGroup(Base):
    """Группа навыков (backend, frontend и т.д.)."""
    __tablename__ = "skill_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("skill_groups.id"))

    skills: Mapped[List["Skill"]] = relationship(
        secondary=skill_group_association,
        back_populates="groups"
    )
    children: Mapped[List["SkillGroup"]] = relationship("SkillGroup")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Skill(Base):
    """Навык в словаре."""
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    normalized_name: Mapped[str] = mapped_column(String(200), index=True)
    aliases: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    embedding: Mapped[Optional[str]] = mapped_column(Text)

    groups: Mapped[List["SkillGroup"]] = relationship(
        secondary=skill_group_association,
        back_populates="skills"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Candidate(Base):
    """Кандидат."""
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))

    birth_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    city: Mapped[Optional[str]] = mapped_column(String(200))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    relocation_ready: Mapped[bool] = mapped_column(Boolean, default=False)

    desired_salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    desired_salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(10), default="RUB")
    work_format: Mapped[Optional[str]] = mapped_column(String(50))
    employment_type: Mapped[Optional[str]] = mapped_column(String(50))

    specialization_group: Mapped[Optional[str]] = mapped_column(String(100))
    position_title: Mapped[Optional[str]] = mapped_column(String(300))

    total_experience_months: Mapped[Optional[int]] = mapped_column(Integer)

    is_active_search: Mapped[bool] = mapped_column(Boolean, default=True)
    current_employer: Mapped[Optional[str]] = mapped_column(String(300))

    about: Mapped[Optional[str]] = mapped_column(Text)

    profile_embedding: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profiles: Mapped[List["CandidateProfile"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    skills: Mapped[List["CandidateSkill"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    education: Mapped[List["Education"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    work_experience: Mapped[List["WorkExperience"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    vacancy_matches: Mapped[List["CandidateVacancyMatch"]] = relationship(back_populates="candidate")

    __table_args__ = (
        Index("idx_candidate_city", "city"),
        Index("idx_candidate_specialization", "specialization_group"),
    )


class CandidateProfile(Base):
    """Профиль кандидата из источника (HH и т.д.)."""
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))

    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(255))
    profile_url: Mapped[Optional[str]] = mapped_column(String(500))

    raw_data: Mapped[Optional[str]] = mapped_column(Text)

    resume_url: Mapped[Optional[str]] = mapped_column(String(500))

    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="profiles")

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_profile_source_external_id"),
    )


class CandidateSkill(Base):
    """Связь кандидата с навыком."""
    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))

    level: Mapped[Optional[str]] = mapped_column(String(50))

    experience_months: Mapped[Optional[int]] = mapped_column(Integer)

    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime)

    source: Mapped[Optional[str]] = mapped_column(String(50))

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_source: Mapped[Optional[str]] = mapped_column(String(100))

    candidate: Mapped["Candidate"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship()

    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )


class Education(Base):
    """Образование кандидата."""
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))

    institution: Mapped[str] = mapped_column(String(500))
    institution_normalized: Mapped[Optional[str]] = mapped_column(String(500))

    faculty: Mapped[Optional[str]] = mapped_column(String(500))
    specialization: Mapped[Optional[str]] = mapped_column(String(500))

    degree: Mapped[Optional[str]] = mapped_column(String(100))

    start_year: Mapped[Optional[int]] = mapped_column(Integer)
    end_year: Mapped[Optional[int]] = mapped_column(Integer)

    university_rating: Mapped[Optional[float]] = mapped_column(Float)
    average_ege_score: Mapped[Optional[float]] = mapped_column(Float)

    candidate: Mapped["Candidate"] = relationship(back_populates="education")


class WorkExperience(Base):
    """Опыт работы; ``end_date`` null означает текущее место."""
    __tablename__ = "work_experience"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))

    company: Mapped[str] = mapped_column(String(500))
    company_normalized: Mapped[Optional[str]] = mapped_column(String(500))

    position: Mapped[str] = mapped_column(String(500))

    description: Mapped[Optional[str]] = mapped_column(Text)

    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    duration_months: Mapped[Optional[int]] = mapped_column(Integer)

    company_rating: Mapped[Optional[float]] = mapped_column(Float)

    candidate: Mapped["Candidate"] = relationship(back_populates="work_experience")


class Vacancy(Base):
    """Вакансия."""
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)

    company: Mapped[str] = mapped_column(String(500))
    company_normalized: Mapped[Optional[str]] = mapped_column(String(500))

    salary_from: Mapped[Optional[int]] = mapped_column(Integer)
    salary_to: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(10), default="RUB")
    salary_gross: Mapped[bool] = mapped_column(Boolean, default=True)

    experience_from: Mapped[Optional[int]] = mapped_column(Integer)
    experience_to: Mapped[Optional[int]] = mapped_column(Integer)

    city: Mapped[Optional[str]] = mapped_column(String(200))
    work_format: Mapped[Optional[str]] = mapped_column(String(50))
    employment_type: Mapped[Optional[str]] = mapped_column(String(50))

    specialization_group: Mapped[Optional[str]] = mapped_column(String(100))

    source: Mapped[Optional[str]] = mapped_column(String(50))
    external_id: Mapped[Optional[str]] = mapped_column(String(255))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))

    description_embedding: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    employer_id: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skills: Mapped[List["VacancySkill"]] = relationship(back_populates="vacancy", cascade="all, delete-orphan")
    candidate_matches: Mapped[List["CandidateVacancyMatch"]] = relationship(back_populates="vacancy")

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_vacancy_source_external_id"),
        Index("idx_vacancy_city", "city"),
        Index("idx_vacancy_specialization", "specialization_group"),
    )


class VacancySkill(Base):
    """Требуемый навык вакансии."""
    __tablename__ = "vacancy_skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))

    is_required: Mapped[bool] = mapped_column(Boolean, default=True)

    required_level: Mapped[Optional[str]] = mapped_column(String(50))

    required_experience_months: Mapped[Optional[int]] = mapped_column(Integer)

    vacancy: Mapped["Vacancy"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship()

    __table_args__ = (
        UniqueConstraint("vacancy_id", "skill_id", name="uq_vacancy_skill"),
    )


class CandidateVacancyMatch(Base):
    """Результат матчинга кандидата с вакансией."""
    __tablename__ = "candidate_vacancy_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"))

    total_score: Mapped[float] = mapped_column(Float)

    skills_score: Mapped[float] = mapped_column(Float, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, default=0.0)
    education_score: Mapped[float] = mapped_column(Float, default=0.0)
    salary_score: Mapped[float] = mapped_column(Float, default=0.0)
    location_score: Mapped[float] = mapped_column(Float, default=0.0)
    embedding_score: Mapped[float] = mapped_column(Float, default=0.0)

    github_score: Mapped[Optional[float]] = mapped_column(Float)

    score_details: Mapped[Optional[str]] = mapped_column(Text)

    employer_status: Mapped[Optional[str]] = mapped_column(String(50))
    employer_notes: Mapped[Optional[str]] = mapped_column(Text)

    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="vacancy_matches")
    vacancy: Mapped["Vacancy"] = relationship(back_populates="candidate_matches")

    __table_args__ = (
        UniqueConstraint("candidate_id", "vacancy_id", name="uq_candidate_vacancy_match"),
        Index("idx_match_total_score", "total_score"),
    )
