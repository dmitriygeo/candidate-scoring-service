
from __future__ import annotations

from typing import List, Optional

from app.models.schemas import (
    CandidateResponse,
    VacancyResponse,
    WorkFormatEnum,
    SpecializationGroupEnum,
)


def _enum_label(val) -> str:
    if val is None:
        return ""
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


def _work_format_ru(wf: Optional[WorkFormatEnum]) -> str:
    if wf is None:
        return ""
    m = {
        "remote": "удалённо",
        "office": "офис",
        "hybrid": "гибрид",
    }
    return m.get(_enum_label(wf), _enum_label(wf))


def _specialization_ru(sg: Optional[SpecializationGroupEnum]) -> str:
    if sg is None:
        return ""
    m = {
        "backend": "Backend",
        "frontend": "Frontend",
        "fullstack": "Fullstack",
        "data_science": "Data Science",
        "data_engineering": "Data Engineering",
        "ml_engineer": "ML Engineer",
        "devops": "DevOps",
        "qa": "QA",
        "mobile": "Mobile",
        "system_analyst": "Системный аналитик",
        "product_manager": "Product Manager",
        "project_manager": "Project Manager",
        "other": "Другое",
    }
    return m.get(_enum_label(sg), _enum_label(sg))


def _months_to_years_label(months: Optional[int]) -> str:
    if months is None or months <= 0:
        return ""
    y = max(1, round(months / 12))
    if y == 1:
        return "1 год"
    if 2 <= y <= 4:
        return f"{y} года"
    return f"{y} лет"


def build_resume_text(candidate: CandidateResponse) -> str:
    """Текст в формате, совместимом с ``FIELD_ALIASES`` / ``extract_field``."""
    lines: List[str] = []
    pos = (candidate.position_title or "").strip()
    if pos:
        lines.append(f"Желаемая должность: {pos}")
    spec = _specialization_ru(candidate.specialization_group)
    if spec:
        lines.append(f"Типовая позиция: {spec}")
        lines.append(f"Профсфера: {spec}")
        lines.append(f"Профессиональная сфера: {spec}")

    skills = [s.skill_name for s in candidate.skills if s.skill_name]
    if skills:
        joined = ", ".join(skills)
        lines.append(f"Hard skills: {joined}")
        lines.append(f"Навыки: {joined}")

    exp_line = _months_to_years_label(candidate.total_experience_months)
    if exp_line:
        lines.append(f"Опыт: {exp_line}")

    city = (candidate.city or "").strip()
    if city:
        lines.append(f"Город: {city}")
        lines.append(f"Регион: {city}")

    wf = _work_format_ru(candidate.work_format)
    if wf:
        lines.append(f"Формат работы: {wf}")

    if candidate.about:
        lines.append(f"О себе: {candidate.about.strip()}")

    return "\n".join(lines)


def build_vacancy_text(vacancy: VacancyResponse) -> str:
    lines: List[str] = []
    title = (vacancy.title or "").strip()
    if title:
        lines.append(f"Название вакансии: {title}")

    spec = _specialization_ru(vacancy.specialization_group)
    if spec:
        lines.append(f"Профессиональная сфера: {spec}")
        lines.append(f"Профсфера: {spec}")

    skills = [s.skill_name for s in vacancy.skills if s.skill_name]
    if skills:
        joined = ", ".join(skills)
        lines.append(f"Hard skills: {joined}")
        lines.append(f"Навыки: {joined}")

    req_parts: List[str] = []
    if vacancy.description:
        req_parts.append(vacancy.description.strip())
    if skills:
        req_parts.append("Ключевые навыки: " + ", ".join(skills))
    if req_parts:
        lines.append("Требования: " + " ".join(req_parts))

    exp_parts: List[str] = []
    if vacancy.experience_from is not None:
        exp_parts.append(f"от {vacancy.experience_from}")
    if vacancy.experience_to is not None:
        exp_parts.append(f"до {vacancy.experience_to}")
    if exp_parts:
        lines.append(f"Опыт: {' '.join(exp_parts)} лет")

    city = (vacancy.city or "").strip()
    if city:
        lines.append(f"Регион: {city}")

    wf = _work_format_ru(vacancy.work_format)
    if wf:
        lines.append(f"Формат работы: {wf}")

    return "\n".join(lines)
