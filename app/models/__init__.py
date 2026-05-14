"""Реэкспорт ORM и Pydantic-схем."""

from .database import (
    Base,
    Candidate,
    CandidateProfile,
    Vacancy,
    Skill,
    CandidateSkill,
    VacancySkill,
    Education,
    WorkExperience,
    CandidateVacancyMatch,
    SkillGroup,
)

from .schemas import (
    CandidateCreate,
    CandidateResponse,
    VacancyCreate,
    VacancyResponse,
    SkillSchema,
    MatchResult,
    CandidateProfileSchema,
)

__all__ = [
    "Base",
    "Candidate",
    "CandidateProfile",
    "Vacancy",
    "Skill",
    "CandidateSkill",
    "VacancySkill",
    "Education",
    "WorkExperience",
    "CandidateVacancyMatch",
    "SkillGroup",
    "CandidateCreate",
    "CandidateResponse",
    "VacancyCreate",
    "VacancyResponse",
    "SkillSchema",
    "MatchResult",
    "CandidateProfileSchema",
]


