"""
Признаки для гибридного ранкера: поля из текста резюме/вакансии + совпадения.
"""

from __future__ import annotations

import re
from typing import Dict, List

FIELD_ALIASES = {
    "resume_title": ["Желаемая должность", "Типовая позиция"],
    "vacancy_title": ["Название вакансии"],
    "resume_skills": ["Навыки", "Hard skills"],
    "vacancy_skills": ["Навыки", "Hard skills", "Требования"],
    "resume_exp": ["Опыт"],
    "vacancy_exp": ["Опыт", "Требования"],
    "resume_region": ["Город", "Регион"],
    "vacancy_region": ["Регион"],
    "resume_sphere": ["Профсфера", "Профессиональная сфера"],
    "vacancy_sphere": ["Профессиональная сфера", "Профсфера"],
}

ALL_FIELD_NAMES = sorted(
    {x for vals in FIELD_ALIASES.values() for x in vals}, key=len, reverse=True
)

RANKER_FEATURE_NAMES: List[str] = [
    "bi_score",
    "cross_score",
    "tfidf_score",
    "token_jaccard",
    "token_overlap_ratio",
    "title_jaccard",
    "title_overlap_ratio",
    "title_prefix_match",
    "skills_jaccard",
    "skills_overlap_ratio",
    "sphere_jaccard",
    "exact_region_match",
    "region_token_overlap",
    "r_years",
    "v_years",
    "years_gap",
    "years_match_0",
    "years_match_1",
    "resume_len_tokens",
    "vacancy_len_tokens",
]

STOPWORDS = {
    "и",
    "в",
    "на",
    "по",
    "с",
    "для",
    "или",
    "от",
    "до",
    "под",
    "над",
    "из",
    "к",
    "a",
    "the",
    "of",
    "to",
    "for",
    "and",
    "or",
    "не",
    "но",
    "что",
    "как",
}


def clean_text(text) -> str:
    if text is None:
        return ""
    s = str(text).strip()
    if not s or s.lower() == "nan":
        return ""
    return " ".join(s.split())


def extract_field(text: str, field_names: List[str]) -> str:
    text = clean_text(text)
    field_pat = "|".join([re.escape(x) for x in ALL_FIELD_NAMES])
    for name in field_names:
        pattern = re.compile(
            re.escape(name) + r":\s*(.*?)(?=(?:" + field_pat + r")\s*:|$)"
        )
        m = pattern.search(text)
        if m:
            val = m.group(1).strip()
            if val:
                return val
    return ""


def tokenize(text: str) -> List[str]:
    toks = re.findall(
        r"[A-Za-zА-Яа-я0-9_+#.-]+", clean_text(text).lower()
    )
    return [t for t in toks if len(t) > 1 and t not in STOPWORDS]


def jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def overlap_ratio(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, min(len(sa), len(sb)))


def extract_years(text: str) -> int:
    text = clean_text(text).lower()
    stripped = text.strip()
    m_full = re.fullmatch(r"(\d+)", stripped)
    if m_full:
        return int(m_full.group(1))
    nums: List[int] = []
    for pat in [
        r"(\d+)\s*лет",
        r"(\d+)\s*года",
        r"(\d+)\s*год",
        r"от\s*(\d+)",
        r"более\s*(\d+)",
    ]:
        nums.extend(int(x) for x in re.findall(pat, text))
    return max(nums) if nums else 0


def startswith_match(a: str, b: str) -> float:
    a = clean_text(a).lower()
    b = clean_text(b).lower()
    if not a or not b:
        return 0.0
    return 1.0 if a.startswith(b) or b.startswith(a) else 0.0


def feature_row(resume_text: str, vacancy_text: str) -> Dict[str, float]:
    r_text = clean_text(resume_text)
    v_text = clean_text(vacancy_text)

    r_title = extract_field(r_text, FIELD_ALIASES["resume_title"])
    v_title = extract_field(v_text, FIELD_ALIASES["vacancy_title"])
    r_skills = extract_field(r_text, FIELD_ALIASES["resume_skills"])
    v_skills = extract_field(v_text, FIELD_ALIASES["vacancy_skills"])
    r_exp = extract_field(r_text, FIELD_ALIASES["resume_exp"])
    v_exp = extract_field(v_text, FIELD_ALIASES["vacancy_exp"])
    r_region = extract_field(r_text, FIELD_ALIASES["resume_region"])
    v_region = extract_field(v_text, FIELD_ALIASES["vacancy_region"])
    r_sphere = extract_field(r_text, FIELD_ALIASES["resume_sphere"])
    v_sphere = extract_field(v_text, FIELD_ALIASES["vacancy_sphere"])

    r_tokens = tokenize(r_text)
    v_tokens = tokenize(v_text)
    r_title_toks = tokenize(r_title)
    v_title_toks = tokenize(v_title)
    r_skill_toks = tokenize(r_skills)
    v_skill_toks = tokenize(v_skills)
    r_sphere_toks = tokenize(r_sphere)
    v_sphere_toks = tokenize(v_sphere)

    r_years = extract_years(r_exp)
    v_years = extract_years(v_exp)
    years_gap = abs(r_years - v_years) if (r_years > 0 and v_years > 0) else 99

    return {
        "token_jaccard": jaccard(r_tokens, v_tokens),
        "token_overlap_ratio": overlap_ratio(r_tokens, v_tokens),
        "title_jaccard": jaccard(r_title_toks, v_title_toks),
        "title_overlap_ratio": overlap_ratio(r_title_toks, v_title_toks),
        "title_prefix_match": startswith_match(r_title, v_title),
        "skills_jaccard": jaccard(r_skill_toks, v_skill_toks),
        "skills_overlap_ratio": overlap_ratio(r_skill_toks, v_skill_toks),
        "sphere_jaccard": jaccard(r_sphere_toks, v_sphere_toks),
        "exact_region_match": 1.0
        if clean_text(r_region).lower()
        and clean_text(r_region).lower() == clean_text(v_region).lower()
        else 0.0,
        "region_token_overlap": jaccard(tokenize(r_region), tokenize(v_region)),
        "r_years": float(r_years),
        "v_years": float(v_years),
        "years_gap": float(years_gap),
        "years_match_0": 1.0 if years_gap == 0 else 0.0,
        "years_match_1": 1.0 if years_gap <= 1 else 0.0,
        "resume_len_tokens": float(len(r_tokens)),
        "vacancy_len_tokens": float(len(v_tokens)),
    }


def vector_for_pair(
    resume_text: str,
    vacancy_text: str,
    bi: float,
    cross: float,
    tfidf: float,
    feature_names: List[str],
) -> List[float]:
    
    r = clean_text(resume_text)
    v = clean_text(vacancy_text)
    fr = feature_row(r, v)
    out: List[float] = []
    for name in feature_names:
        if name == "bi_score":
            out.append(float(bi))
        elif name == "cross_score":
            out.append(float(cross))
        elif name == "tfidf_score":
            out.append(float(tfidf))
        else:
            out.append(float(fr[name]))
    return out
