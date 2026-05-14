
from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING, List, Optional, Tuple

from loguru import logger

if TYPE_CHECKING:
    from spacy.language import Language

    from app.services.skills import SkillNormalizer

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    spacy = None  # type: ignore
    SPACY_AVAILABLE = False

_lock = threading.Lock()
_nlp_by_normalizer_id: dict[int, "Language"] = {}


def reset_skill_ner_models() -> None:
    with _lock:
        _nlp_by_normalizer_id.clear()


def _build_entity_ruler_patterns(nlp: "Language", normalizer: "SkillNormalizer") -> List[dict]:
    surfaces = normalizer.iter_surface_forms_for_ner()
    patterns: List[dict] = []
    seen_json: set[str] = set()

    for surface in surfaces:
        if len(surface) > 100:
            continue
        doc = nlp.make_doc(surface)
        if len(doc) == 0 or len(doc) > 14:
            continue
        patt = [{"LOWER": tok.text.lower()} for tok in doc]
        key = json.dumps(patt, ensure_ascii=False)
        if key in seen_json:
            continue
        seen_json.add(key)
        patterns.append({"label": "SKILL", "pattern": patt})

    return patterns


def _make_nlp_for_normalizer(normalizer: "SkillNormalizer") -> Optional["Language"]:
    if not SPACY_AVAILABLE:
        logger.warning("spaCy не установлен — NER по навыкам отключён")
        return None

    from config import settings

    if not getattr(settings, "NER_ENABLED", True):
        return None

    nlp = spacy.blank("xx")
    ruler = nlp.add_pipe("entity_ruler")
    patterns = _build_entity_ruler_patterns(nlp, normalizer)
    ruler.add_patterns(patterns)
    logger.info(
        f"Skill NER (EntityRuler): {len(patterns)} уникальных паттернов "
        f"из {len(normalizer.iter_surface_forms_for_ner())} поверхностных форм"
    )
    return nlp


def get_skill_ner_nlp(normalizer: Optional["SkillNormalizer"] = None) -> Optional["Language"]:
    """
    Возвращает spaCy Language с entity_ruler по словарю навыков.
    Кэшируется по id экземпляра SkillNormalizer.
    """
    from app.services.skills import SkillNormalizer

    nz = normalizer or SkillNormalizer()
    key = id(nz)

    with _lock:
        if key in _nlp_by_normalizer_id:
            return _nlp_by_normalizer_id[key]

        nlp = _make_nlp_for_normalizer(nz)
        if nlp is not None:
            _nlp_by_normalizer_id[key] = nlp
        return nlp


def extract_dictionary_skill_spans(
    text: str,
    normalizer: Optional["SkillNormalizer"] = None,
) -> List[Tuple[str, int, int, str]]:
    """
    Извлекает сущности навыков из текста.

    Returns:
        Список кортежей (surface_text, start_char, end_char, label).
    """
    if not text or not text.strip():
        return []

    nlp = get_skill_ner_nlp(normalizer)
    if nlp is None:
        return []

    doc = nlp(text)
    return [(ent.text, ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]
