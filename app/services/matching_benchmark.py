
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from app.models.schemas import (
    CandidateResponse,
    CandidateSkillSchema,
    VacancyResponse,
    VacancySkillSchema,
    WorkFormatEnum,
)

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _vacancy_skill(s: Dict[str, Any], idx: int) -> VacancySkillSchema:
    return VacancySkillSchema(
        skill_id=int(s.get("skill_id", idx)),
        skill_name=s["skill_name"],
        is_required=bool(s.get("is_required", True)),
    )


def _candidate_skill(name: str, idx: int) -> CandidateSkillSchema:
    return CandidateSkillSchema(skill_id=1000 + idx, skill_name=name)


def vacancy_from_payload(p: Dict[str, Any]) -> VacancyResponse:
    skills = [_vacancy_skill(s, i) for i, s in enumerate(p.get("skills", []))]
    wf = p.get("work_format")
    return VacancyResponse(
        id=int(p["id"]),
        title=p["title"],
        description=p.get("description"),
        company=p.get("company", "Company"),
        city=p.get("city"),
        work_format=WorkFormatEnum(wf) if wf else None,
        experience_from=p.get("experience_from"),
        experience_to=p.get("experience_to"),
        salary_from=p.get("salary_from"),
        salary_to=p.get("salary_to"),
        skills=skills,
        created_at=_now(),
        updated_at=_now(),
    )


def candidate_from_payload(p: Dict[str, Any]) -> CandidateResponse:
    skills = [_candidate_skill(n, i) for i, n in enumerate(p.get("skills", []))]
    wf = p.get("work_format")
    return CandidateResponse(
        id=int(p["id"]),
        position_title=p.get("position_title"),
        about=p.get("about"),
        city=p.get("city"),
        work_format=WorkFormatEnum(wf) if wf else None,
        total_experience_months=p.get("total_experience_months"),
        desired_salary_min=p.get("desired_salary_min"),
        desired_salary_max=p.get("desired_salary_max"),
        skills=skills,
        education=[],
        work_experience=[],
        profiles=[],
        created_at=_now(),
        updated_at=_now(),
    )


def load_generated_ranking_benchmark() -> List[Tuple[str, VacancyResponse, List[CandidateResponse], Set[int]]]:
    path = Path(__file__).resolve().parent.parent / "data" / "matching_generated_benchmark.json"
    return load_ranking_benchmark(path)


def load_ranking_benchmark(
    path: str | Path | None = None,
) -> List[Tuple[str, VacancyResponse, List[CandidateResponse], Set[int]]]:
    """
    Returns:
        Список кортежей (scenario_name, vacancy, candidates, relevant_ids).
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "matching_rank_benchmark.json"
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    out: List[Tuple[str, VacancyResponse, List[CandidateResponse], Set[int]]] = []
    for sc in data["scenarios"]:
        name = sc["name"]
        rel = {int(x) for x in sc["relevant_candidate_ids"]}
        vac = vacancy_from_payload(sc["vacancy"])
        cands = [candidate_from_payload(c) for c in sc["candidates"]]
        out.append((name, vac, cands, rel))
    return out


def required_skill_ids(vacancy: VacancyResponse) -> Set[int]:

    req = {s.skill_id for s in vacancy.skills if s.is_required}
    if req:
        return req
    return {s.skill_id for s in vacancy.skills}


def candidate_required_skill_coverage(candidate: CandidateResponse, required_ids: Set[int]) -> float:
    if not required_ids:
        return 1.0
    have = {s.skill_id for s in candidate.skills}
    return len(have & required_ids) / len(required_ids)


def relevant_ids_by_required_skill_coverage(
    candidates: List[CandidateResponse],
    vacancy: VacancyResponse,
    min_coverage: float,
) -> Set[int]:
    req = required_skill_ids(vacancy)
    rel: Set[int] = set()
    for c in candidates:
        if candidate_required_skill_coverage(c, req) >= min_coverage:
            rel.add(c.id)
    return rel
