
from __future__ import annotations

from copy import deepcopy
from statistics import mean, pstdev
from typing import Callable, List, Set

from app.models.schemas import MatchResult
from app.services.matching import MatchWeights


def weighted_total(m: MatchResult, w: MatchWeights) -> float:
    """Линейная комбинация компонентов как в MatchingService."""
    w = deepcopy(w)
    w.normalize()
    return (
        w.skills * m.skills_score
        + w.experience * m.experience_score
        + w.education * m.education_score
        + w.salary * m.salary_score
        + w.location * m.location_score
        + w.embedding * m.embedding_score
    )


WEIGHT_PRESETS: dict[str, MatchWeights] = {
    "baseline": MatchWeights(0.35, 0.20, 0.10, 0.10, 0.10, 0.15),
    "skill_first": MatchWeights(0.52, 0.18, 0.08, 0.07, 0.07, 0.08),
    "semantic_first": MatchWeights(0.22, 0.15, 0.07, 0.07, 0.04, 0.45),
    "skills_only": MatchWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "embedding_only": MatchWeights(0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
}


def sort_matches_by_score(
    matches: List[MatchResult],
    score_fn: Callable[[MatchResult], float],
) -> List[MatchResult]:
    out = sorted(matches, key=score_fn, reverse=True)
    for i, m in enumerate(out, 1):
        m.rank = i
    return out


def rank_by_weight_preset(matches: List[MatchResult], preset: str) -> List[MatchResult]:
    w = WEIGHT_PRESETS[preset]
    return sort_matches_by_score(matches, lambda m: weighted_total(m, w))


def rrf_rerank(matches: List[MatchResult], k_rrf: float = 60.0) -> List[MatchResult]:
    """
    Reciprocal Rank Fusion: объединение двух ранжирований (эмбеддинг и навыки).
    Cormack et al., «Reciprocal Rank Fusion outperforms Condorcet...», SIGIR 2009.
    """
    by_emb = sorted(matches, key=lambda m: m.embedding_score, reverse=True)
    by_sk = sorted(matches, key=lambda m: m.skills_score, reverse=True)
    r_emb = {m.candidate_id: i for i, m in enumerate(by_emb, start=1)}
    r_sk = {m.candidate_id: i for i, m in enumerate(by_sk, start=1)}

    def rrf_score(m: MatchResult) -> float:
        return 1.0 / (k_rrf + r_emb[m.candidate_id]) + 1.0 / (k_rrf + r_sk[m.candidate_id])

    return sort_matches_by_score(matches, rrf_score)


def two_stage_embedding_pool_then_skill_first(
    matches: List[MatchResult],
    top_fraction: float = 0.65,
) -> List[MatchResult]:
    """
    Двухстадийно: пул кандидатов по эмбеддингу, затем ранжирование skill_first внутри пула.
    Остальные кандидаты остаются в хвосте с низким приоритетом (как грубый retrieve-then-rerank).
    """
    if not matches:
        return []
    n_pool = max(1, int(len(matches) * top_fraction))
    by_emb = sorted(matches, key=lambda m: m.embedding_score, reverse=True)
    pool: Set[int] = {m.candidate_id for m in by_emb[:n_pool]}
    w = WEIGHT_PRESETS["skill_first"]

    def score(m: MatchResult) -> float:
        if m.candidate_id not in pool:
            return -1e9 + weighted_total(m, w) * 1e-6
        return weighted_total(m, w)

    return sort_matches_by_score(matches, score)


def comb_sum_component_scores(matches: List[MatchResult]) -> List[MatchResult]:
    """
    CombSUM-стиль: сумма компонентных скоров как отдельных «систем» (Fox & Shaw, SIGIR 1993).
    Здесь все сигналы уже в [0,1], веса равны для наглядной абляции.
    """
    return sort_matches_by_score(
        matches,
        lambda m: (
            m.skills_score
            + m.embedding_score
            + m.experience_score
            + m.education_score
            + m.salary_score
            + m.location_score
        ),
    )


def _zscores(values: List[float]) -> List[float]:
    if not values:
        return []
    mu = mean(values)
    sd = pstdev(values)
    if sd < 1e-12:
        return [0.0 for _ in values]
    return [(v - mu) / sd for v in values]


def zscore_fusion_emb_skill(matches: List[MatchResult]) -> List[MatchResult]:
    """
    Fusion нормализованных по пулу кандидатов z-scores эмбеддинга и навыков
    (score-based metasearch / late fusion в духе Montague & Aslam, CIKM 2002).
    """
    if not matches:
        return []
    ze = _zscores([m.embedding_score for m in matches])
    zs = _zscores([m.skills_score for m in matches])
    by_id = {m.candidate_id: ze[i] + zs[i] for i, m in enumerate(matches)}
    return sort_matches_by_score(matches, lambda m: by_id[m.candidate_id])


def convex_dense_sparse_fusion(
    matches: List[MatchResult],
    *,
    alpha: float = 0.55,
) -> List[MatchResult]:
    """
    Выпуклая комбинация dense (эмбеддинг) и sparse-подобного (навыки) сигналов.
    См. обсуждение hybrid retrieval + reranking (Nogueira & Cho, 2019; Lin et al., pretraining for IR).
    """
    a = min(1.0, max(0.0, alpha))
    return sort_matches_by_score(
        matches,
        lambda m: a * m.embedding_score + (1.0 - a) * m.skills_score,
    )


def product_emb_skill(matches: List[MatchResult]) -> List[MatchResult]:
    """Произведение dense × skills — жёстче, чем среднее: оба канала должны быть высокими."""
    return sort_matches_by_score(
        matches,
        lambda m: m.embedding_score * m.skills_score,
    )


def harmonic_mean_emb_skill(matches: List[MatchResult]) -> List[MatchResult]:
    """Harmonic mean — штраф за дисбаланс между каналами (robust fusion / conservative retrieval)."""
    return sort_matches_by_score(
        matches,
        lambda m: (
            0.0
            if m.embedding_score <= 0 or m.skills_score <= 0
            else 2.0 * m.embedding_score * m.skills_score / (m.embedding_score + m.skills_score)
        ),
    )
