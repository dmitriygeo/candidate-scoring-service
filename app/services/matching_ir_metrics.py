"""
Метрики качества ранжирования
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

import numpy as np


def dcg_at_k(relevances: Sequence[float], k: int) -> float:
    s = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        s += float(rel) / float(np.log2(i + 1))
    return s


def ndcg_at_k(relevances_in_model_order: Sequence[float], k: int) -> float:
    rel = list(relevances_in_model_order)
    d = dcg_at_k(rel, k)
    ideal = sorted(rel, reverse=True)
    idcg = dcg_at_k(ideal, k)
    return (d / idcg) if idcg > 0 else 0.0


def mrr(relevances_in_model_order: Sequence[float]) -> float:
    for i, r in enumerate(relevances_in_model_order, start=1):
        if r > 0:
            return 1.0 / i
    return 0.0


def average_precision_binary(relevances_in_model_order: Sequence[float]) -> float:

    rels = list(relevances_in_model_order)
    R = sum(1 for r in rels if r > 0)
    if R == 0:
        return 0.0
    acc = 0.0
    seen = 0
    for i, r in enumerate(rels, start=1):
        if r > 0:
            seen += 1
            acc += seen / i
    return acc / R


def precision_at_k(relevances_in_model_order: Sequence[float], k: int) -> float:

    rels = list(relevances_in_model_order[:k])
    if not rels:
        return 0.0
    return float(sum(1 for r in rels if r > 0)) / float(min(k, len(rels)))


def relevances_for_ranking(
    ranked_candidate_ids: Iterable[int],
    relevant_ids: set,
) -> List[float]:
    return [1.0 if int(cid) in relevant_ids else 0.0 for cid in ranked_candidate_ids]


def summarize_ranking_metrics(
    ranked_candidate_ids: Sequence[int],
    relevant_ids: set,
    k_list: Sequence[int] = (5, 10),
) -> dict:
    rel = relevances_for_ranking(ranked_candidate_ids, relevant_ids)
    out: dict = {
        "mrr": mrr(rel),
        "map": average_precision_binary(rel),
    }
    for k in k_list:
        out[f"ndcg@{k}"] = ndcg_at_k(rel, k)
        out[f"p@{k}"] = precision_at_k(rel, k)
    return out


def mean_over_queries(query_metrics: List[dict]) -> dict:

    if not query_metrics:
        return {}
    keys = [
        k
        for k, v in query_metrics[0].items()
        if isinstance(v, (int, float, np.integer, np.floating))
    ]
    return {key: float(np.mean([float(qm[key]) for qm in query_metrics])) for key in keys}
