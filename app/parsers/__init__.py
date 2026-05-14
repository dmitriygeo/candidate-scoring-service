"""
Парсеры данных из различных источников
"""

from .base import BaseParser
from .hh_vacancies import HHVacancyParser
from .hh_resumes import HHResumeParser
from .superjob import SuperJobParser
from .habr_career import HabrCareerParser

__all__ = [
    "BaseParser",
    "HHVacancyParser",
    "HHResumeParser",
    "SuperJobParser",
    "HabrCareerParser",
]


