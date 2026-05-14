"""Нормализация навыков, группы, покрытие для матчинга."""

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from loguru import logger

from app.models.schemas import SpecializationGroupEnum


@dataclass
class SkillInfo:
    name: str
    normalized_name: str
    aliases: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    level_keywords: Dict[str, List[str]] = field(default_factory=dict)


class SkillNormalizer:

    _MAX_PHRASE_TOKENS = 8

    def __init__(self, dictionary_path: Optional[str] = None):
        self._skills: Dict[str, SkillInfo] = {}
        self._alias_map: Dict[str, str] = {}
        self._group_skills: Dict[str, Set[str]] = {}

        if dictionary_path:
            self.load_dictionary(dictionary_path)
        else:
            default_path = Path(__file__).parent.parent / "data" / "skills_dictionary.json"
            if default_path.exists():
                self.load_dictionary(str(default_path))
    
    def load_dictionary(self, path: str):
        """Загрузка словаря навыков из JSON файла"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for group_name, group_data in data.get("groups", {}).items():
                self._group_skills[group_name] = set()
                
                for skill_data in group_data.get("skills", []):
                    skill_name = skill_data["name"]
                    normalized = self._normalize_string(skill_name)

                    if normalized not in self._skills:
                        self._skills[normalized] = SkillInfo(
                            name=skill_name,
                            normalized_name=normalized,
                            aliases=skill_data.get("aliases", []),
                            groups=[group_name],
                            level_keywords=skill_data.get("level_keywords", {})
                        )
                    else:
                        if group_name not in self._skills[normalized].groups:
                            self._skills[normalized].groups.append(group_name)

                    self._alias_map[normalized] = normalized

                    for alias in skill_data.get("aliases", []):
                        normalized_alias = self._normalize_string(alias)
                        self._alias_map[normalized_alias] = normalized

                    self._group_skills[group_name].add(normalized)
            
            logger.info(f"Загружено {len(self._skills)} навыков из словаря")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки словаря навыков: {e}")
    
    @staticmethod
    def _normalize_string(s: str) -> str:
        """Нормализация строки для сравнения (ключи алиасов)."""
        s = unicodedata.normalize("NFC", s).strip().lower()
        s = (
            s.replace("c++", "cplusplus")
            .replace("c#", "csharp")
            .replace("f#", "fsharp")
        )
        s = re.sub(r"[^\w\s]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _longest_phrase_alias(self, normalized_input: str) -> Optional[str]:
        """Longest token-phrase из ввода, совпадающая с ключом словаря; при равенстве длины — лекс. минимум."""
        words = normalized_input.split()
        if not words:
            return None
        max_n = min(self._MAX_PHRASE_TOKENS, len(words))
        best_canonical: Optional[str] = None
        best_n = 0
        for i in range(len(words)):
            for n in range(min(max_n, len(words) - i), 0, -1):
                phrase = " ".join(words[i : i + n])
                if phrase not in self._alias_map:
                    continue
                c = self._alias_map[phrase]
                if n > best_n or (n == best_n and (best_canonical is None or c < best_canonical)):
                    best_n = n
                    best_canonical = c
        return best_canonical

    def _resolve(self, skill: str) -> Tuple[Optional[str], Optional[SkillInfo]]:
        """Общая логика: точное совпадение ключа, затем longest token-phrase match."""
        raw = skill.strip()
        if not raw:
            return None, None
        normalized_input = self._normalize_string(raw)
        if not normalized_input:
            return None, None
        if normalized_input in self._alias_map:
            canonical = self._alias_map[normalized_input]
            info = self._skills[canonical]
            return info.name, info
        canonical = self._longest_phrase_alias(normalized_input)
        if canonical is not None:
            info = self._skills[canonical]
            return info.name, info
        return None, None

    def normalize(self, skill: str) -> Optional[str]:
        """
        Нормализация навыка

        Args:
            skill: Исходное название навыка

        Returns:
            Нормализованное название или None если навык не найден
        """
        name, _ = self._resolve(skill)
        return name

    def normalize_legacy(self, skill: str) -> Optional[str]:
        """
        Прежняя эвристика (подстрочные совпадения в произвольном порядке обхода словаря).
        Сохранена для сравнения качества в экспериментах и ноутбуках.
        """
        normalized_input = self._normalize_string(skill)
        if not normalized_input:
            return None
        if normalized_input in self._alias_map:
            canonical = self._alias_map[normalized_input]
            return self._skills[canonical].name
        for alias, canonical in self._alias_map.items():
            if alias in normalized_input or normalized_input in alias:
                return self._skills[canonical].name
        return None

    def normalize_with_info(self, skill: str) -> Tuple[Optional[str], Optional[SkillInfo]]:
        """
        Нормализация с возвратом полной информации о навыке

        Returns:
            (нормализованное_название, информация_о_навыке)
        """
        return self._resolve(skill)

    def iter_surface_forms_for_ner(self) -> List[str]:
        """
        Уникальные строки для словарного NER: канонические имена и алиасы
        (без дубликатов по регистру).
        """
        seen: Set[str] = set()
        out: List[str] = []
        for info in self._skills.values():
            for s in [info.name, *(info.aliases or [])]:
                t = (s or "").strip()
                if not t:
                    continue
                key = t.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(t)
        return out

    def get_skill_groups(self, skill: str) -> List[str]:
        """Получить группы, к которым относится навык"""
        normalized_name, skill_info = self.normalize_with_info(skill)
        
        if skill_info:
            return skill_info.groups
        
        return []
    
    def get_group_skills(self, group: str) -> List[str]:
        """Получить все навыки группы"""
        if group in self._group_skills:
            return [
                self._skills[s].name 
                for s in self._group_skills[group] 
                if s in self._skills
            ]
        return []
    
    def fuzzy_match(self, skill: str, threshold: float = 0.8) -> Optional[str]:
        """
        Нечёткое сопоставление навыка (для опечаток)
        
        Args:
            skill: Входной навык
            threshold: Порог сходства (0-1)
            
        Returns:
            Наиболее подходящий навык или None
        """
        from difflib import SequenceMatcher
        
        normalized_input = self._normalize_string(skill)
        
        best_match = None
        best_score = threshold
        
        for alias in self._alias_map.keys():
            score = SequenceMatcher(None, normalized_input, alias).ratio()
            if score >= best_score:
                best_score = score
                best_match = self._alias_map[alias]
        
        if best_match:
            return self._skills[best_match].name
        
        return None
    
    def normalize_list(
        self,
        skills: List[str],
        use_fuzzy: bool = True
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Нормализация списка навыков
        
        Args:
            skills: Список исходных навыков
            use_fuzzy: Использовать нечёткое сопоставление
            
        Returns:
            Список кортежей (исходный_навык, нормализованный_навык)
        """
        results = []
        
        for skill in skills:
            normalized = self.normalize(skill)
            
            if not normalized and use_fuzzy:
                normalized = self.fuzzy_match(skill)
            
            results.append((skill, normalized))
        
        return results


class SkillsService:
    """
    Сервис для работы с навыками
    """
    
    def __init__(self, dictionary_path: Optional[str] = None):
        self.normalizer = SkillNormalizer(dictionary_path)
        self._group_mapping = self._build_group_mapping()
    
    def _build_group_mapping(self) -> Dict[str, SpecializationGroupEnum]:
        """Маппинг названий групп на enum"""
        return {
            "backend": SpecializationGroupEnum.BACKEND,
            "frontend": SpecializationGroupEnum.FRONTEND,
            "data_science": SpecializationGroupEnum.DATA_SCIENCE,
            "data_engineering": SpecializationGroupEnum.DATA_ENGINEERING,
            "devops": SpecializationGroupEnum.DEVOPS,
            "mobile": SpecializationGroupEnum.MOBILE,
            "qa": SpecializationGroupEnum.QA,
        }
    
    def normalize_skills(
        self,
        skills: List[str]
    ) -> List[str]:
        """
        Нормализация списка навыков
        
        Args:
            skills: Список исходных навыков
            
        Returns:
            Список уникальных нормализованных навыков
        """
        normalized = set()
        
        for skill in skills:
            norm_skill = self.normalizer.normalize(skill)
            if norm_skill:
                normalized.add(norm_skill)
            else:
                normalized.add(skill.strip().title())
        
        return list(normalized)
    
    def detect_specialization(
        self,
        skills: List[str]
    ) -> Optional[SpecializationGroupEnum]:
        """
        Определение специализации по списку навыков
        
        Args:
            skills: Список навыков
            
        Returns:
            Наиболее вероятная специализация
        """
        group_scores: Dict[str, int] = {}
        
        for skill in skills:
            groups = self.normalizer.get_skill_groups(skill)
            for group in groups:
                group_scores[group] = group_scores.get(group, 0) + 1
        
        if not group_scores:
            return None

        best_group = max(group_scores, key=group_scores.get)
        
        return self._group_mapping.get(best_group)
    
    def calculate_skills_coverage(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        optional_skills: Optional[List[str]] = None
    ) -> Dict:
        """Покрытие обязательных/опциональных навыков; при отсутствии требований по вакансии ``total_score`` = 0."""
        def _non_empty(names: Optional[List[str]]) -> List[str]:
            if not names:
                return []
            out: List[str] = []
            for x in names:
                if x is None:
                    continue
                s = str(x).strip()
                if s:
                    out.append(s)
            return out

        candidate_normalized = set(
            self.normalize_skills(_non_empty(candidate_skills))
        )
        required_normalized = set(
            self.normalize_skills(_non_empty(required_skills))
        )
        optional_normalized = set(
            self.normalize_skills(_non_empty(optional_skills or []))
        )
        candidate_normalized.discard("")
        required_normalized.discard("")
        optional_normalized.discard("")

        matched_required = candidate_normalized & required_normalized
        missing_required = required_normalized - candidate_normalized
        
        required_coverage = (
            len(matched_required) / len(required_normalized)
            if required_normalized else 1.0
        )

        matched_optional = candidate_normalized & optional_normalized
        missing_optional = optional_normalized - candidate_normalized
        
        optional_coverage = (
            len(matched_optional) / len(optional_normalized)
            if optional_normalized else 0.0
        )

        extra_skills = candidate_normalized - required_normalized - optional_normalized

        has_req = bool(required_normalized)
        has_opt = bool(optional_normalized)
        if not has_req and not has_opt:
            blend_total = 0.0
        elif has_req and has_opt:
            blend_total = required_coverage * 0.8 + optional_coverage * 0.2
        elif has_req:
            blend_total = required_coverage
        elif has_opt:
            blend_total = optional_coverage
        
        return {
            "required_coverage": required_coverage,
            "optional_coverage": optional_coverage,
            "matched_required": list(matched_required),
            "missing_required": list(missing_required),
            "matched_optional": list(matched_optional),
            "missing_optional": list(missing_optional),
            "extra_skills": list(extra_skills),
            "total_score": blend_total,
        }
    
    def find_similar_skills(
        self,
        skill: str,
        limit: int = 5
    ) -> List[str]:
        """
        Поиск похожих навыков
        
        Args:
            skill: Навык для поиска похожих
            limit: Максимальное количество результатов
            
        Returns:
            Список похожих навыков
        """
        groups = self.normalizer.get_skill_groups(skill)
        
        if not groups:
            return []
        
        similar = set()
        for group in groups:
            group_skills = self.normalizer.get_group_skills(group)
            similar.update(group_skills)

        normalized_skill = self.normalizer.normalize(skill)
        if normalized_skill in similar:
            similar.remove(normalized_skill)
        
        return list(similar)[:limit]
    
    def get_all_groups(self) -> List[Dict]:
        """Получить информацию о всех группах навыков"""
        groups = []
        
        for group_name, enum_value in self._group_mapping.items():
            skills = self.normalizer.get_group_skills(group_name)
            groups.append({
                "name": group_name,
                "enum": enum_value.value,
                "skills_count": len(skills),
                "skills": skills
            })
        
        return groups


