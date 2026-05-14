"""Парсер вакансий HeadHunter (публичное API api.hh.ru)."""

from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from loguru import logger

from .base import BaseParser
from app.models.schemas import (
    ParsedVacancy,
    SourceTypeEnum,
    WorkFormatEnum,
    EmploymentTypeEnum,
)
from config import settings


class HHVacancyParser(BaseParser[ParsedVacancy]):
    """GET /vacancies и /vacancies/{id} → ``ParsedVacancy``."""
    
    source = SourceTypeEnum.HH
    base_url = "https://api.hh.ru"
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }
        
        if settings.HH_API_TOKEN:
            headers["Authorization"] = f"Bearer {settings.HH_API_TOKEN}"
        
        return headers
    
    async def parse_list(
        self,
        query: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
        area: Optional[int] = None,
        experience: Optional[str] = None,
        employment: Optional[str] = None,
        schedule: Optional[str] = None,
        professional_role: Optional[int] = None,
        **filters
    ) -> List[ParsedVacancy]:
        """Поиск вакансий (параметры как у API HH: area, experience, employment, schedule)."""
        params = {
            "page": page,
            "per_page": min(per_page, 100),
            "only_with_salary": False,
        }
        
        if query:
            params["text"] = query
        if area:
            params["area"] = area
        if experience:
            params["experience"] = experience
        if employment:
            params["employment"] = employment
        if schedule:
            params["schedule"] = schedule
        if professional_role:
            params["professional_role"] = professional_role
        
        try:
            response = await self.get(f"{self.base_url}/vacancies", params=params)
            data = response.json()
            
            vacancies = []
            for item in data.get("items", []):
                vacancy = self._parse_vacancy_item(item, detailed=False)
                if vacancy:
                    vacancies.append(vacancy)
            
            logger.info(f"[HH] Найдено вакансий: {data.get('found', 0)}, на странице: {len(vacancies)}")
            return vacancies
        
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 403:
                logger.error(f"[HH] Доступ запрещён (403). Возможно, нужен API токен или слишком много запросов.")
            elif status == 429:
                logger.error(f"[HH] Слишком много запросов (429). Подождите и попробуйте снова.")
            else:
                logger.error(f"[HH] HTTP ошибка {status}: {e.response.text[:200]}")
            return []
            
        except Exception as e:
            error_msg = str(e)
            if "RetryError" in error_msg:
                logger.error(f"[HH] Все попытки запроса исчерпаны. Возможные причины: "
                            f"блокировка IP, нужен токен, или сервис недоступен.")
            else:
                logger.error(f"[HH] Ошибка парсинга списка вакансий: {e}")
            return []
    
    async def parse_item(self, item_id: str) -> Optional[ParsedVacancy]:
        """Детали вакансии по id."""
        try:
            response = await self.get(f"{self.base_url}/vacancies/{item_id}")
            data = response.json()
            
            return self._parse_vacancy_item(data, detailed=True)
            
        except Exception as e:
            logger.error(f"[HH] Ошибка парсинга вакансии {item_id}: {e}")
            return None
    
    def _parse_vacancy_item(
        self,
        data: Dict[str, Any],
        detailed: bool = False
    ) -> Optional[ParsedVacancy]:
        """JSON элемента или детального ответа HH → ``ParsedVacancy``."""
        try:
            salary = data.get("salary") or {}
            salary_from, salary_to, currency, gross = self.parse_salary(salary)
            
            experience = data.get("experience") or {}
            experience_months = self._parse_hh_experience(experience.get("id"))
            
            area = data.get("area") or {}
            city = area.get("name")
            
            schedule = data.get("schedule") or {}
            work_format = self._map_schedule_to_work_format(schedule.get("id"))
            
            employment = data.get("employment") or {}
            employment_type = self._map_employment_type(employment.get("id"))
            
            skills_raw = []
            
            for skill in data.get("key_skills", []):
                if skill.get("name"):
                    skills_raw.append(skill["name"])
            
            description = None
            if detailed:
                description = self.clean_html(data.get("description"))
            else:
                snippet = data.get("snippet") or {}
                req = (snippet.get("requirement") or "").strip()
                resp = (snippet.get("responsibility") or "").strip()
                parts_snip = []
                if req:
                    parts_snip.append(f"Требования: {req}")
                if resp:
                    parts_snip.append(f"Обязанности: {resp}")
                description = self.clean_html("\n\n".join(parts_snip) if parts_snip else None)
            description = self._ensure_description_sections(description, detailed=detailed)
            
            employer = data.get("employer") or {}
            company = employer.get("name", "Unknown")
            
            published_at = None
            if data.get("published_at"):
                try:
                    published_at = datetime.fromisoformat(
                        data["published_at"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass
            
            return ParsedVacancy(
                source=self.source,
                external_id=str(data["id"]),
                source_url=data.get("alternate_url"),
                title=data.get("name", ""),
                company=company,
                description=description,
                salary_from=salary_from,
                salary_to=salary_to,
                salary_currency=currency,
                salary_gross=gross,
                experience_from=experience_months,
                experience_to=None,
                city=city,
                work_format=work_format,
                employment_type=employment_type,
                skills_raw=skills_raw,
                published_at=published_at,
                raw_data=data if detailed else None
            )
            
        except Exception as e:
            logger.error(f"[HH] Ошибка парсинга вакансии: {e}")
            return None
    
    @staticmethod
    def _ensure_description_sections(
        description: Optional[str], *, detailed: bool
    ) -> Optional[str]:
        """Один формат с импортом train_IT: блоки ``## заголовок``, если их ещё нет в тексте."""
        if not description or not str(description).strip():
            return description
        d = str(description).strip()
        if "##" in d:
            return d
        heading = "О вакансии" if detailed else "Краткое описание"
        return f"## {heading}\n{d}"
    
    @staticmethod
    def _parse_hh_experience(experience_id: Optional[str]) -> Optional[int]:
        """Код опыта HH → нижняя граница в месяцах."""
        mapping = {
            "noExperience": 0,
            "between1And3": 12,
            "between3And6": 36,
            "moreThan6": 72,
        }
        return mapping.get(experience_id)
    
    @staticmethod
    def _map_schedule_to_work_format(schedule_id: Optional[str]) -> Optional[WorkFormatEnum]:
        """График HH → ``WorkFormatEnum``."""
        mapping = {
            "remote": WorkFormatEnum.REMOTE,
            "fullDay": WorkFormatEnum.OFFICE,
            "shift": WorkFormatEnum.OFFICE,
            "flexible": WorkFormatEnum.HYBRID,
            "flyInFlyOut": WorkFormatEnum.OFFICE,
        }
        return mapping.get(schedule_id)
    
    @staticmethod
    def _map_employment_type(employment_id: Optional[str]) -> Optional[EmploymentTypeEnum]:
        """Тип занятости HH → ``EmploymentTypeEnum``."""
        mapping = {
            "full": EmploymentTypeEnum.FULL_TIME,
            "part": EmploymentTypeEnum.PART_TIME,
            "project": EmploymentTypeEnum.PROJECT,
            "probation": EmploymentTypeEnum.INTERNSHIP,
        }
        return mapping.get(employment_id)
    
    async def search_by_specialization(
        self,
        specialization: str,
        area: int = 113,
        page: int = 0,
        per_page: int = 20
    ) -> List[ParsedVacancy]:
        """Поиск по ключу специализации (backend, frontend, …) через заготовленный текстовый запрос."""
        specialization_queries = {
            "backend": "backend developer OR бэкенд разработчик",
            "frontend": "frontend developer OR фронтенд разработчик",
            "fullstack": "fullstack developer OR full stack разработчик",
            "data_science": "data scientist OR аналитик данных OR ML engineer",
            "data_engineering": "data engineer OR инженер данных",
            "devops": "devops OR site reliability engineer OR SRE",
            "qa": "QA engineer OR тестировщик",
            "mobile": "mobile developer OR iOS OR Android разработчик",
        }
        
        query = specialization_queries.get(specialization, specialization)
        
        return await self.parse_list(
            query=query,
            area=area,
            page=page,
            per_page=per_page
        )


