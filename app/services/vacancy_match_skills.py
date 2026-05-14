"""
Дополнение списка навыков вакансии навыками из текста описания (и заголовка) для матчинга.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app.models.schemas import VacancyResponse, VacancySkillSchema
from app.services.skill_extractor import SkillExtractor

if TYPE_CHECKING:
    from app.services.database import DatabaseService


def merge_skills_from_vacancy_description(
    vacancy: VacancyResponse,
    skill_extractor: SkillExtractor,
    db: DatabaseService,
) -> VacancyResponse:
    """
    Объединяет навыки из ``vacancy.skills`` с навыками, извлечёнными из ``title`` и ``description``.

    Новые позиции добавляются как обязательные (``is_required=True``) — при матчинге все навыки
    вакансии считаются обязательными. Дубликаты по ``skill_id`` и по нормализованному имени
    отбрасываются.
    """
    title = (vacancy.title or "").strip()
    desc = (vacancy.description or "").strip()
    if not desc and not title:
        return vacancy

    extraction = skill_extractor.extract_from_vacancy(
        title=title,
        description=desc or title,
    )

    normalizer = skill_extractor.skills_service.normalizer
    existing_ids = {s.skill_id for s in vacancy.skills}

    def norm_key(name: str) -> str:
        n = normalizer.normalize(name or "")
        return (n or name or "").strip().lower()

    existing_norm = {norm_key(s.skill_name) for s in vacancy.skills if s.skill_name}

    merged: list[VacancySkillSchema] = list(vacancy.skills)
    added = 0

    for es in extraction.skills:
        if es.confidence < skill_extractor.config.min_confidence:
            continue
        label = (es.normalized_name or es.name or "").strip()
        if not label:
            continue
        nk = norm_key(es.name) or norm_key(label)
        if nk and nk in existing_norm:
            continue

        skill_row = db.get_or_create_skill(es.normalized_name or es.name)
        if skill_row.id in existing_ids:
            if nk:
                existing_norm.add(nk)
            continue

        existing_ids.add(skill_row.id)
        if nk:
            existing_norm.add(nk)

        merged.append(
            VacancySkillSchema(
                skill_id=skill_row.id,
                skill_name=skill_row.name,
                is_required=True,
                required_level=None,
                required_experience_months=None,
            )
        )
        added += 1

    if added:
        logger.debug(
            "Вакансия {}: к матчингу добавлено {} навыков из описания/заголовка",
            vacancy.id,
            added,
        )

    return vacancy.model_copy(update={"skills": merged})
