"""Извлечение навыков из текста резюме и вакансий"""

import re
from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass

from loguru import logger

from app.models.schemas import (
    ExtractedSkill,
    NerSpan,
    SkillExtractionResult,
    SkillLevelEnum,
    SpecializationGroupEnum,
)
from app.services.skills import SkillsService, SkillNormalizer


@dataclass
class ExtractionConfig:
    """Параметры извлечения навыков."""
    min_confidence: float = 0.5
    use_context_analysis: bool = True
    extract_level_hints: bool = True
    max_skills: int = 50
    use_ner: bool = True


class SkillExtractor:
    """NER по словарю, regex, списки через запятую, нормализация и уровень по контексту."""

    def __init__(
        self,
        skills_service: Optional[SkillsService] = None,
        config: Optional[ExtractionConfig] = None
    ):
        self.skills_service = skills_service or SkillsService()
        self.config = config or ExtractionConfig()

        self._technology_patterns = self._build_technology_patterns()
        self._level_patterns = self._build_level_patterns()
        self._experience_patterns = self._build_experience_patterns()

    def _build_technology_patterns(self) -> List[re.Pattern]:
        """Regex-кандидаты на названия технологий."""
        patterns = [
            r'\b([A-Z][a-zA-Z]+(?:\s*\d+(?:\.\d+)*)?)(?:\s|,|;|$)',
            r'\b([A-Z][a-z]+[A-Z][a-zA-Z]*)\b',
            r'\b([A-Z]?[a-z]+\.(?:js|ts|NET|io))\b',
            r'\b([A-Z]{2,6})\b',
            r'\b([a-z]+_[a-z]+(?:_[a-z]+)*)\b',
        ]
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def _build_level_patterns(self) -> Dict[SkillLevelEnum, List[re.Pattern]]:
        """Паттерны уровня владения по контексту."""
        patterns = {
            SkillLevelEnum.BEGINNER: [
                re.compile(r'базов\w*\s+(?:знани|уровен|опыт)', re.I),
                re.compile(r'начальн\w*\s+(?:уровен|опыт)', re.I),
                re.compile(r'junior|джуниор|начинающ', re.I),
                re.compile(r'basic\s+knowledge', re.I),
            ],
            SkillLevelEnum.INTERMEDIATE: [
                re.compile(r'средн\w*\s+уровен', re.I),
                re.compile(r'уверенн\w*\s+(?:владени|знани|пользовател)', re.I),
                re.compile(r'middle|мидл', re.I),
                re.compile(r'good\s+knowledge', re.I),
            ],
            SkillLevelEnum.ADVANCED: [
                re.compile(r'продвинут\w*|глубок\w*', re.I),
                re.compile(r'senior|сеньор|старш', re.I),
                re.compile(r'expert\s+level', re.I),
                re.compile(r'extensive\s+experience', re.I),
            ],
            SkillLevelEnum.EXPERT: [
                re.compile(r'эксперт|гуру|профессионал', re.I),
                re.compile(r'lead|лид|ведущ', re.I),
                re.compile(r'architect|архитектор', re.I),
                re.compile(r'deep\s+expertise', re.I),
            ],
        }
        return patterns

    def _build_experience_patterns(self) -> List[Tuple[re.Pattern, int]]:
        """Паттерны длительности опыта (множитель → месяцы)."""
        return [
            (re.compile(r'(\d+)\+?\s*(?:лет|года?|years?)', re.I), 12),
            (re.compile(r'(\d+)\+?\s*(?:месяц\w*|months?)', re.I), 1),
            (re.compile(r'более\s+(\d+)\s*(?:лет|года?)', re.I), 12),
            (re.compile(r'от\s+(\d+)\s*(?:лет|года?)', re.I), 12),
        ]

    def extract_skills(
        self,
        text: str,
        context: Optional[str] = None,
        include_ner_spans: bool = False,
    ) -> SkillExtractionResult:
        """Извлечь навыки из текста; при include_ner_spans добавить сырые спаны NER."""
        if not text:
            return SkillExtractionResult(
                skills=[],
                specialization_group=None,
                raw_text="",
                ner_spans=[] if include_ner_spans else None,
            )

        text = self._preprocess_text(text)

        need_ner = self.config.use_ner or include_ner_spans
        ner_tuples: List[Tuple[str, int, int, str]] = []
        if need_ner:
            from app.services.ner_service import extract_dictionary_skill_spans

            ner_tuples = extract_dictionary_skill_spans(
                text, self.skills_service.normalizer
            )

        ner_spans_out: Optional[List[NerSpan]] = None
        if include_ner_spans:
            ner_spans_out = [
                NerSpan(text=t, label=lab, start=s, end=e)
                for t, s, e, lab in ner_tuples
            ]

        candidates = self._extract_skill_candidates(text, ner_tuples)

        extracted_skills = []
        seen_skills: Set[str] = set()

        for candidate, context_snippet, source in candidates:
            normalized = self.skills_service.normalizer.normalize(candidate)

            if normalized and normalized not in seen_skills:
                seen_skills.add(normalized)

                level = None
                if self.config.extract_level_hints:
                    level = self._detect_skill_level(context_snippet)

                confidence = self._calculate_confidence(
                    candidate, normalized, context_snippet
                )
                if source == "ner":
                    confidence = min(1.0, confidence + 0.12)

                if confidence >= self.config.min_confidence:
                    extracted_skills.append(
                        ExtractedSkill(
                            name=candidate,
                            normalized_name=normalized,
                            confidence=confidence,
                            context=context_snippet[:100] if context_snippet else None,
                            level_hint=level,
                        )
                    )

        extracted_skills = sorted(
            extracted_skills,
            key=lambda s: s.confidence,
            reverse=True
        )[:self.config.max_skills]

        skill_names = [s.normalized_name for s in extracted_skills]
        specialization = self.skills_service.detect_specialization(skill_names)

        return SkillExtractionResult(
            skills=extracted_skills,
            specialization_group=specialization,
            raw_text=text,
            ner_spans=ner_spans_out,
        )

    def _preprocess_text(self, text: str) -> str:
        """Убрать HTML и лишние пробелы."""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[\n\r\t]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_skill_candidates(
        self,
        text: str,
        ner_tuples: List[Tuple[str, int, int, str]],
    ) -> List[Tuple[str, str, str]]:
        """Кортежи (кандидат, контекст, источник: regex | list | ner)."""
        candidates: List[Tuple[str, str, str]] = []

        sentences = re.split(r"[.!?;]", text)

        for sentence in sentences:
            for pattern in self._technology_patterns:
                matches = pattern.finditer(sentence)
                for match in matches:
                    skill = match.group(1).strip()

                    if len(skill) >= 2 and not self._is_stopword(skill):
                        start = max(0, match.start() - 50)
                        end = min(len(sentence), match.end() + 50)
                        ctx = sentence[start:end]

                        candidates.append((skill, ctx, "regex"))

        list_items = re.findall(
            r"(?:^|[,;•\-–])\s*([A-Za-z][A-Za-z0-9\+\#\.]+(?:\s+\d+(?:\.\d+)*)?)",
            text,
        )
        for item in list_items:
            item = item.strip()
            if len(item) >= 2 and not self._is_stopword(item):
                candidates.append((item, "", "list"))

        for surface, start, end, _lab in ner_tuples:
            surface = surface.strip()
            if len(surface) < 2:
                continue
            ctx_start = max(0, start - 50)
            ctx_end = min(len(text), end + 50)
            ctx = text[ctx_start:ctx_end]
            candidates.append((surface, ctx, "ner"))

        return candidates

    def _is_stopword(self, word: str) -> bool:
        """Служебные слова, не считающиеся навыками."""
        stopwords = {
            'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'от', 'до', 'на', 'по', 'из', 'за', 'при', 'об', 'без',
            'год', 'года', 'лет', 'месяц', 'опыт', 'работа', 'знание',
            'year', 'years', 'month', 'months', 'experience', 'knowledge',
            'и', 'или', 'не', 'как', 'что', 'это',
        }
        return word.lower() in stopwords

    def _detect_skill_level(
        self,
        context: str
    ) -> Optional[SkillLevelEnum]:
        """Уровень по фрагменту контекста."""
        if not context:
            return None

        for level, patterns in self._level_patterns.items():
            for pattern in patterns:
                if pattern.search(context):
                    return level

        return None

    def _calculate_confidence(
        self,
        original: str,
        normalized: str,
        context: str
    ) -> float:
        """Эвристическая уверенность (словарь, длина, ключевые слова в контексте)."""
        confidence = 0.5

        if original.lower() == normalized.lower():
            confidence += 0.3

        if len(original) >= 5:
            confidence += 0.1

        context_keywords = ['опыт', 'знание', 'владение', 'работа', 'experience', 'skills', 'knowledge']
        if context and any(kw in context.lower() for kw in context_keywords):
            confidence += 0.1

        return min(1.0, confidence)

    def extract_experience_from_text(
        self,
        text: str,
        skill: str
    ) -> Optional[int]:
        """Опыт с навыком в месяцах по тексту рядом с упоминанием."""
        skill_pattern = re.escape(skill)

        patterns = [
            rf'{skill_pattern}\s*[-–:]\s*(\d+)\+?\s*(?:лет|года?|years?)',
            rf'{skill_pattern}\s*[-–:]\s*(\d+)\+?\s*(?:месяц\w*|months?)',
            rf'(\d+)\+?\s*(?:лет|года?|years?)\s+(?:опыт\w*\s+)?(?:работы?\s+)?(?:с\s+)?{skill_pattern}',
            rf'(\d+)\+?\s*(?:месяц\w*|months?)\s+(?:опыт\w*\s+)?{skill_pattern}',
        ]

        for pattern, multiplier in zip(patterns, [12, 1, 12, 1]):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1)) * multiplier
                except (ValueError, IndexError):
                    continue

        return None

    def extract_from_vacancy(
        self,
        title: str,
        description: str,
        requirements: Optional[str] = None
    ) -> SkillExtractionResult:
        """Навыки из полей вакансии."""
        full_text = f"{title}\n{description}"
        if requirements:
            full_text += f"\n{requirements}"

        return self.extract_skills(full_text, context=title)

    def extract_from_resume(
        self,
        position: Optional[str],
        about: Optional[str],
        experience_descriptions: Optional[List[str]] = None,
        skills_list: Optional[List[str]] = None
    ) -> SkillExtractionResult:
        """Навыки из резюме плюс структурированный список навыков."""
        parts = []

        if position:
            parts.append(position)

        if about:
            parts.append(about)

        if experience_descriptions:
            parts.extend(experience_descriptions)

        full_text = "\n".join(parts)

        result = self.extract_skills(full_text, context=position)

        if skills_list:
            existing_normalized = {s.normalized_name for s in result.skills}

            for skill in skills_list:
                normalized = self.skills_service.normalizer.normalize(skill)
                if normalized and normalized not in existing_normalized:
                    existing_normalized.add(normalized)
                    result.skills.append(ExtractedSkill(
                        name=skill,
                        normalized_name=normalized,
                        confidence=1.0,
                        context=None,
                        level_hint=None
                    ))

        return result


class SkillsAggregator:
    """Объединение навыков из нескольких извлечений."""

    def __init__(self, skills_service: Optional[SkillsService] = None):
        self.skills_service = skills_service or SkillsService()

    def aggregate(
        self,
        extractions: List[SkillExtractionResult]
    ) -> List[ExtractedSkill]:
        """Слить по normalized_name: макс. confidence, бонус за несколько источников."""
        skill_map: Dict[str, ExtractedSkill] = {}

        for extraction in extractions:
            for skill in extraction.skills:
                key = skill.normalized_name

                if key not in skill_map:
                    skill_map[key] = skill
                else:
                    existing = skill_map[key]

                    if skill.confidence > existing.confidence:
                        skill_map[key] = ExtractedSkill(
                            name=skill.name,
                            normalized_name=skill.normalized_name,
                            confidence=skill.confidence,
                            context=skill.context or existing.context,
                            level_hint=skill.level_hint or existing.level_hint
                        )
                    elif skill.level_hint and not existing.level_hint:
                        skill_map[key] = ExtractedSkill(
                            name=existing.name,
                            normalized_name=existing.normalized_name,
                            confidence=existing.confidence,
                            context=existing.context,
                            level_hint=skill.level_hint
                        )

                    skill_map[key] = ExtractedSkill(
                        name=skill_map[key].name,
                        normalized_name=skill_map[key].normalized_name,
                        confidence=min(1.0, skill_map[key].confidence + 0.1),
                        context=skill_map[key].context,
                        level_hint=skill_map[key].level_hint
                    )

        return sorted(
            skill_map.values(),
            key=lambda s: s.confidence,
            reverse=True
        )
