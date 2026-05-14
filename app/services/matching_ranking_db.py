
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from app.models.schemas import CandidateResponse, VacancyResponse
from app.services.matching_benchmark import relevant_ids_by_required_skill_coverage


def _slug_title(title: str, max_len: int = 36) -> str:
    s = re.sub(r"\s+", "_", title.strip().lower())
    s = re.sub(r"[^a-z0-9а-яё_]+", "", s, flags=re.IGNORECASE)
    return (s[:max_len] or "vacancy").rstrip("_")


def sqlite_database_file_path(base_dir: Path | None = None) -> Path | None:
    from config import resolved_sqlite_database_path

    _ = base_dir
    return resolved_sqlite_database_path()


def load_ranking_benchmark_from_db(
    session: Any,
    *,
    max_scenarios: int = 8,
    pool_size: int = 20,
    min_candidates_in_pool: int = 8,
    min_description_len: int = 40,
    min_vacancy_skills: int = 1,
    from_matches_limit: int = 12,
    coverage_threshold: float = 0.55,
    min_matches_per_vacancy: int = 6,
) -> Tuple[List[Tuple[str, VacancyResponse, List[CandidateResponse], Set[int]]], Dict[str, Any]]:
    from sqlalchemy import func

    from app.models.database import Candidate, CandidateVacancyMatch, Vacancy, VacancySkill
    from app.services.database import DatabaseService

    db = DatabaseService(session)

    match_stats = (
        session.query(
            CandidateVacancyMatch.vacancy_id,
            func.count(CandidateVacancyMatch.id).label("cnt"),
        )
        .group_by(CandidateVacancyMatch.vacancy_id)
        .having(func.count(CandidateVacancyMatch.id) >= min_matches_per_vacancy)
        .order_by(func.count(CandidateVacancyMatch.id).desc())
        .limit(max_scenarios * 4)
        .all()
    )
    vacancy_id_order = [row[0] for row in match_stats]

    scenarios: List[Tuple[str, VacancyResponse, List[CandidateResponse], Set[int]]] = []
    meta: Dict[str, Any] = {
        "source": "database",
        "coverage_threshold": coverage_threshold,
        "pool_size": pool_size,
        "skipped": [],
    }

    for vid in vacancy_id_order:
        if len(scenarios) >= max_scenarios:
            break
        v = session.get(Vacancy, vid)
        if v is None or not v.description or len(v.description.strip()) < min_description_len:
            meta["skipped"].append({"vacancy_id": vid, "reason": "short_or_missing_description"})
            continue

        n_skills = (
            session.query(func.count(VacancySkill.id))
            .filter(VacancySkill.vacancy_id == vid)
            .scalar()
        ) or 0
        if n_skills < min_vacancy_skills:
            meta["skipped"].append(
                {"vacancy_id": vid, "reason": "too_few_vacancy_skills", "n_skills": n_skills}
            )
            continue

        match_rows = (
            session.query(CandidateVacancyMatch)
            .filter_by(vacancy_id=vid)
            .order_by(CandidateVacancyMatch.total_score.desc())
            .limit(from_matches_limit)
            .all()
        )
        ordered_ids: List[int] = []
        seen: Set[int] = set()
        for m in match_rows:
            if m.candidate_id not in seen:
                ordered_ids.append(m.candidate_id)
                seen.add(m.candidate_id)

        need = max(0, pool_size - len(ordered_ids))
        q = session.query(Candidate)
        if ordered_ids:
            q = q.filter(~Candidate.id.in_(ordered_ids))
        extras: List[Any] = list(q.order_by(func.random()).limit(need).all())

        cand_orm: List[Any] = []
        for cid in ordered_ids:
            c = session.get(Candidate, cid)
            if c is not None:
                cand_orm.append(c)
        for c in extras:
            if c.id not in seen:
                cand_orm.append(c)
                seen.add(c.id)

        if len(cand_orm) < min_candidates_in_pool:
            meta["skipped"].append({"vacancy_id": vid, "reason": "too_few_candidates_in_pool"})
            continue

        vac_resp = db.vacancy_to_response(v)
        cand_responses = [db.candidate_to_response(c) for c in cand_orm]
        rel = relevant_ids_by_required_skill_coverage(cand_responses, vac_resp, coverage_threshold)
        non_rel = [c for c in cand_responses if c.id not in rel]
        if not rel or not non_rel:
            meta["skipped"].append(
                {
                    "vacancy_id": vid,
                    "reason": "no_binary_mix",
                    "n_relevant": len(rel),
                    "n_irrelevant": len(non_rel),
                }
            )
            continue

        name = f"db_v{v.id}_{_slug_title(v.title or '')}"
        scenarios.append((name, vac_resp, cand_responses, rel))

    meta["n_scenarios"] = len(scenarios)
    return scenarios, meta
