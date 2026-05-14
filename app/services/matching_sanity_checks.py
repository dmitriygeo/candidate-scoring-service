
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.schemas import MatchResult, VacancyResponse


def count_vacancy_skills(v: VacancyResponse) -> int:
    return len([s for s in v.skills if s.skill_name and str(s.skill_name).strip()])


def analyze_match_batch(
    vacancy: VacancyResponse,
    matches: List[MatchResult],
    *,
    hybrid_used: bool,
) -> Dict[str, Any]:

    issues: List[str] = []
    n_sk = count_vacancy_skills(vacancy)
    n_cand = len(matches)

    if n_cand == 0:
        issues.append("Нет ни одного результата после фильтра min_score")

    prev_total: Optional[float] = None
    for i, m in enumerate(matches):
        if m.total_score < 0 or m.total_score > 1:
            issues.append(
                f"candidate_id={m.candidate_id}: total_score={m.total_score} вне [0, 1]"
            )
        for name, val in (
            ("skills_score", m.skills_score),
            ("experience_score", m.experience_score),
            ("education_score", m.education_score),
            ("salary_score", m.salary_score),
            ("location_score", m.location_score),
            ("embedding_score", m.embedding_score),
        ):
            if val < 0 or val > 1:
                issues.append(
                    f"candidate_id={m.candidate_id}: {name}={val} вне [0, 1]"
                )

        det = m.score_details
        if det:
            matched_list = det.matched_skills or []
            missing_req = det.missing_required_skills or []
            mm = len(matched_list)
            mr = len(missing_req)

            if n_sk > 0 and mm == 0 and mr == 0:
                issues.append(
                    f"candidate_id={m.candidate_id}: навыков в вакансии {n_sk}, но "
                    f"matched_skills и missing_required пусты (нормализация/данные?)."
                )

            if n_sk > 0 and m.skills_score == 0.0 and mm > 0:
                issues.append(
                    f"candidate_id={m.candidate_id}: skills_score=0 при ненулевом matched_skills ({mm})."
                )

            if n_sk == 0 and m.skills_score != 0.0:
                issues.append(
                    f"candidate_id={m.candidate_id}: нет структурированных навыков вакансии, "
                    f"но skills_score={m.skills_score} (ожидалось 0)."
                )

        if prev_total is not None and m.total_score > prev_total + 1e-9:
            issues.append(
                f"Нарушен порядок сортировки: rank {i} total={m.total_score} > предыдущего {prev_total}"
            )
        prev_total = m.total_score

    stats = {
        "vacancy_id": vacancy.id,
        "vacancy_skills": n_sk,
        "results": n_cand,
        "hybrid_used": hybrid_used,
        "top_total": matches[0].total_score if matches else None,
        "bottom_total": matches[-1].total_score if matches else None,
    }
    return {"issues": issues, "stats": stats}


def methodology_markdown() -> str:
    return (
        "## Методика и интерпретация\n\n"
        "- Проверяется: все частичные скоры и `total_score` в диапазоне [0, 1]; "
        "убывание `total_score` в выдаче; согласованность блока навыков "
        "(есть навыки вакансии, но 0 совпадений и 0 пропусков — подозрительно; "
        "нет навыков вакансии, но `skills_score` ≠ 0 — противоречие исправлению в `calculate_skills_coverage`).\n"
        "- При включённом гибриде `total_score` — вероятность модели; эвристические поля "
        "(`skills_score`, …) остаются от взвешенной формулы — расхождение с рангом не ошибка.\n"
        "- Скрипт использует тот же `merge_skills_from_vacancy_description`, что и API матчинга.\n"
    )


def summarize_batches(reports: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    all_issues = 0
    for r in reports:
        vid = r["stats"]["vacancy_id"]
        title = r.get("title", "")
        iss = r["issues"]
        all_issues += len(iss)
        lines.append(f"### Вакансия id={vid} — {title[:80]}")
        lines.append(f"- Навыков в карточке: {r['stats']['vacancy_skills']}, результатов: {r['stats']['results']}")
        lines.append(f"- Hybrid: {r['stats']['hybrid_used']}")
        if iss:
            for x in iss:
                lines.append(f"  - [!] {x}")
        else:
            lines.append("  - [OK] Замеченных логических противоречий нет")
        lines.append("")
    lines.append(f"**Всего замечаний:** {all_issues}")
    return "\n".join(lines)
