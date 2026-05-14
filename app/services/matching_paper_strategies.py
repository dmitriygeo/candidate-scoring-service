"""
Стратегии ранжирования, явно привязанные к трём репрезентативным работам по семантическому
сопоставлению вакансий и резюме.

1) **conSultantBERT** — Lavi, Medentsiy, Graus, *conSultantBERT: Fine-tuned Siamese Sentence-BERT
   for Matching Jobs and Job Seekers*, RecSys in HR / arXiv:2109.06501. Би-энкодер SBERT + косинус
   по полным текстам; навыки и прочие сигналы — дополнительные признаки. Здесь: упор на
   ``embedding_score`` с лёгкой регуляризацией по ``skills_score``.

2) **CareerSmart** (гибрид lexical + dense + покрытие навыков) — Pendela et al., *CareerSmart...*
   IJERT 2026 (DOI: 10.5281/zenodo.19033816): skill coverage, TF-IDF-подобная лексика,
   Sentence-BERT. Здесь: ``skills_score`` + ``embedding_score`` + **Jaccard по токенам**
   объединённого текста JD/резюме (прокси TF-IDF / лексического канала без отдельного индекса).

3) **Deep Siamese (IBM WWW'18)** — Malinowski et al., *Matching Resumes to Jobs via Deep Siamese
   Network*, WWW 2018 — CNN над структурированным текстом резюме и JD. Здесь: нет CNN;
   **суррогат** — сбалансированная линейная смесь dense + shallow (навыки + опыт), имитируя
   совместное вложение «семантика + структура».
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from app.models.schemas import CandidateResponse, MatchResult, VacancyResponse
from app.services.matching_strategies import sort_matches_by_score

_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+", re.UNICODE)


def _tokens(text: str | None) -> Set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def vacancy_text_bag(vacancy: VacancyResponse) -> Set[str]:
    """Объединённый лексический мешок вакансии (аналог title+description+skills+компания)."""
    parts = [
        vacancy.title or "",
        vacancy.description or "",
        vacancy.company or "",
    ]
    parts.extend(s.skill_name for s in vacancy.skills)
    bag: Set[str] = set()
    for p in parts:
        bag |= _tokens(p)
    return bag


def candidate_text_bag(candidate: CandidateResponse) -> Set[str]:
    """Резюме: должность, about, навыки (как в статьях по парсингу CV)."""
    parts = [candidate.position_title or "", candidate.about or ""]
    parts.extend(s.skill_name for s in candidate.skills)
    bag: Set[str] = set()
    for p in parts:
        bag |= _tokens(p)
    return bag


def token_jaccard_lexical_channel(vacancy: VacancyResponse, candidate: CandidateResponse) -> float:
    """Лексическое пересечение JD↔CV (дискретный канал; прокси TF-IDF overlap из CareerSmart)."""
    a, b = vacancy_text_bag(vacancy), candidate_text_bag(candidate)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def consultantbert_style_rank(matches: List[MatchResult]) -> List[MatchResult]:
    """
    Siamese bi-encoder + cosine: основной сигнал — плотная семантика (как conSultantBERT),
    небольшой вес навыков как дополнительный признак.
    """
    return sort_matches_by_score(
        matches,
        lambda m: 0.88 * m.embedding_score + 0.12 * m.skills_score,
    )


def careersmart_hybrid_rank(
    matches: List[MatchResult],
    vacancy: VacancyResponse,
    candidates: List[CandidateResponse],
) -> List[MatchResult]:
    """
    Три дополняющих измерения (CareerSmart): покрытие навыков, dense-семантика, лексическое
    пересечение токенов JD/CV.
    """
    by_id: Dict[int, CandidateResponse] = {c.id: c for c in candidates}
    lex: Dict[int, float] = {}
    for m in matches:
        c = by_id.get(m.candidate_id)
        if c is None:
            lex[m.candidate_id] = 0.0
        else:
            lex[m.candidate_id] = token_jaccard_lexical_channel(vacancy, c)

    return sort_matches_by_score(
        matches,
        lambda m: (
            (1.0 / 3.0) * m.skills_score
            + (1.0 / 3.0) * m.embedding_score
            + (1.0 / 3.0) * lex.get(m.candidate_id, 0.0)
        ),
    )


def ibm_siamese_style_rank(matches: List[MatchResult]) -> List[MatchResult]:
    """
    Суррогат глубокого Siamese (IBM WWW'18): совместная проекция «семантика + структурированные»
    сигналы — эмбеддинг, навыки, опыт (вместо CNN по полям резюме).
    """
    return sort_matches_by_score(
        matches,
        lambda m: 0.52 * m.embedding_score + 0.33 * m.skills_score + 0.15 * m.experience_score,
    )
