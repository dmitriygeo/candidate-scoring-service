"""
Парсер вакансий и резюме с SuperJob
https://api.superjob.ru/
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from loguru import logger

from .base import BaseParser
from app.models.schemas import (
    ParsedVacancy,
    ParsedResume,
    SourceTypeEnum,
    WorkFormatEnum,
    EmploymentTypeEnum,
    WorkExperienceBase,
    EducationBase,
)
from config import settings


class SuperJobParser(BaseParser[ParsedVacancy]):
    """
    Парсер SuperJob
    
    Требует API ключ для работы.
    API: https://api.superjob.ru/2.0/
    """
    
    source = SourceTypeEnum.SUPERJOB
    base_url = "https://api.superjob.ru/2.0"
    
    def _get_headers(self) -> Dict[str, str]:
        headers = super()._get_headers()
        
        # SuperJob требует API ключ
        if settings.SUPERJOB_API_KEY:
            headers["X-Api-App-Id"] = settings.SUPERJOB_API_KEY
        
        return headers
    
    async def parse_list(
        self,
        query: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
        town: Optional[int] = None,  # ID города
        catalogues: Optional[int] = None,  # ID каталога профессий
        experience: Optional[int] = None,  # 0=без опыта, 1=1-3, 2=3-6, 3=6+
        type_of_work: Optional[int] = None,  # 6=полная, 10=частичная
        place_of_work: Optional[int] = None,  # 0=офис, 1=удаленная
        **filters
    ) -> List[ParsedVacancy]:
        """
        Поиск вакансий на SuperJob
        
        Args:
            query: Поисковый запрос
            page: Номер страницы
            per_page: Количество на странице (макс 100)
            town: ID города (4=Москва, 14=СПб)
            catalogues: ID каталога (48=IT)
            experience: Опыт работы
            type_of_work: Тип занятости
            place_of_work: Место работы (офис/удаленка)
            
        Returns:
            Список вакансий
        """
        params = {
            "page": page,
            "count": min(per_page, 100),
        }
        
        if query:
            params["keyword"] = query
        if town:
            params["town"] = town
        if catalogues:
            params["catalogues"] = catalogues
        if experience is not None:
            params["experience"] = experience
        if type_of_work:
            params["type_of_work"] = type_of_work
        if place_of_work is not None:
            params["place_of_work"] = place_of_work
        
        try:
            response = await self.get(f"{self.base_url}/vacancies/", params=params)
            data = response.json()
            
            vacancies = []
            for item in data.get("objects", []):
                vacancy = self._parse_vacancy_item(item)
                if vacancy:
                    vacancies.append(vacancy)
            
            logger.info(f"[SuperJob] Найдено вакансий: {data.get('total', 0)}, на странице: {len(vacancies)}")
            return vacancies
            
        except Exception as e:
            logger.error(f"[SuperJob] Ошибка парсинга списка вакансий: {e}")
            return []
    
    async def parse_item(self, item_id: str) -> Optional[ParsedVacancy]:
        """
        Получить детальную информацию о вакансии
        """
        try:
            response = await self.get(f"{self.base_url}/vacancies/{item_id}/")
            data = response.json()
            
            return self._parse_vacancy_item(data)
            
        except Exception as e:
            logger.error(f"[SuperJob] Ошибка парсинга вакансии {item_id}: {e}")
            return None
    
    def _parse_vacancy_item(self, data: Dict[str, Any]) -> Optional[ParsedVacancy]:
        """
        Парсинг данных вакансии SuperJob
        """
        try:
            # Зарплата
            salary_from = data.get("payment_from")
            salary_to = data.get("payment_to")
            currency = data.get("currency", "rub").upper()
            
            # Если зарплата 0, считаем что не указана
            if salary_from == 0:
                salary_from = None
            if salary_to == 0:
                salary_to = None
            
            # Опыт
            experience = data.get("experience") or {}
            experience_months = self._parse_sj_experience(experience.get("id"))
            
            # Город
            town = data.get("town") or {}
            city = town.get("title")
            
            # Формат работы
            place_of_work = data.get("place_of_work") or {}
            work_format = self._map_place_of_work(place_of_work.get("id"))
            
            # Тип занятости
            type_of_work = data.get("type_of_work") or {}
            employment_type = self._map_type_of_work(type_of_work.get("id"))
            
            # Описание
            description = data.get("candidat", "")  # Требования к кандидату
            vacancy_description = data.get("work", "")  # Описание работы
            full_description = f"{vacancy_description}\n\n{description}".strip()
            
            # Навыки (извлекаем из текста, т.к. SJ не даёт структурированно)
            skills_raw = []
            
            # Работодатель
            firm_name = data.get("firm_name", "Unknown")
            
            # Дата публикации
            published_at = None
            if data.get("date_published"):
                try:
                    published_at = datetime.fromtimestamp(data["date_published"])
                except:
                    pass
            
            return ParsedVacancy(
                source=self.source,
                external_id=str(data["id"]),
                source_url=data.get("link"),
                title=data.get("profession", ""),
                company=firm_name,
                description=full_description or None,
                salary_from=salary_from,
                salary_to=salary_to,
                salary_currency=currency,
                salary_gross=True,  # SuperJob по умолчанию показывает gross
                experience_from=experience_months,
                experience_to=None,
                city=city,
                work_format=work_format,
                employment_type=employment_type,
                skills_raw=skills_raw,
                published_at=published_at,
                raw_data=data
            )
            
        except Exception as e:
            logger.error(f"[SuperJob] Ошибка парсинга вакансии: {e}")
            return None
    
    @staticmethod
    def _parse_sj_experience(experience_id: Optional[int]) -> Optional[int]:
        """
        Преобразование опыта SuperJob в месяцы
        """
        mapping = {
            1: 0,   # без опыта
            2: 12,  # от 1 года
            3: 36,  # от 3 лет
            4: 72,  # от 6 лет
        }
        return mapping.get(experience_id)
    
    @staticmethod
    def _map_place_of_work(place_id: Optional[int]) -> Optional[WorkFormatEnum]:
        """
        Маппинг места работы SuperJob
        """
        mapping = {
            0: WorkFormatEnum.OFFICE,
            1: WorkFormatEnum.REMOTE,
        }
        return mapping.get(place_id)
    
    @staticmethod
    def _map_type_of_work(type_id: Optional[int]) -> Optional[EmploymentTypeEnum]:
        """
        Маппинг типа занятости SuperJob
        """
        mapping = {
            6: EmploymentTypeEnum.FULL_TIME,
            10: EmploymentTypeEnum.PART_TIME,
            12: EmploymentTypeEnum.PROJECT,
        }
        return mapping.get(type_id)


class SuperJobResumeParser(BaseParser[ParsedResume]):
    """
    Парсер резюме SuperJob
    
    Примечание: API для резюме требует OAuth авторизацию
    """
    
    source = SourceTypeEnum.SUPERJOB
    base_url = "https://api.superjob.ru/2.0"
    
    def _get_headers(self) -> Dict[str, str]:
        headers = super()._get_headers()
        
        if settings.SUPERJOB_API_KEY:
            headers["X-Api-App-Id"] = settings.SUPERJOB_API_KEY
        
        return headers
    
    async def parse_list(
        self,
        query: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
        **filters
    ) -> List[ParsedResume]:
        """
        Поиск резюме (требует OAuth)
        """
        params = {
            "page": page,
            "count": min(per_page, 100),
        }
        
        if query:
            params["keyword"] = query
        
        try:
            response = await self.get(f"{self.base_url}/resumes/", params=params)
            data = response.json()
            
            resumes = []
            for item in data.get("objects", []):
                resume = self._parse_resume_item(item)
                if resume:
                    resumes.append(resume)
            
            return resumes
            
        except Exception as e:
            logger.error(f"[SuperJob] Ошибка парсинга списка резюме: {e}")
            return []
    
    async def parse_item(self, item_id: str) -> Optional[ParsedResume]:
        """
        Получить детальную информацию о резюме
        """
        try:
            response = await self.get(f"{self.base_url}/resumes/{item_id}/")
            data = response.json()
            
            return self._parse_resume_item(data)
            
        except Exception as e:
            logger.error(f"[SuperJob] Ошибка парсинга резюме {item_id}: {e}")
            return None
    
    def _parse_resume_item(self, data: Dict[str, Any]) -> Optional[ParsedResume]:
        """
        Парсинг резюме SuperJob
        """
        try:
            # Персональные данные
            first_name = data.get("firstname")
            last_name = data.get("lastname")
            middle_name = data.get("middlename")
            
            # Дата рождения
            birth_date = None
            if data.get("birthday"):
                try:
                    birth_date = datetime.fromtimestamp(data["birthday"])
                except:
                    pass
            
            # Город
            town = data.get("town") or {}
            city = town.get("title")
            
            # Желаемая должность и зарплата
            position_title = data.get("profession")
            desired_salary = data.get("payment")
            
            # Общий опыт
            total_experience_months = None
            if data.get("experience_length"):
                total_experience_months = data["experience_length"]
            
            # Опыт работы
            work_experience = []
            for exp in data.get("experience", []):
                work_exp = WorkExperienceBase(
                    company=exp.get("name", ""),
                    position=exp.get("position", ""),
                    description=exp.get("description"),
                    start_date=datetime.fromtimestamp(exp["date_start"]) if exp.get("date_start") else None,
                    end_date=datetime.fromtimestamp(exp["date_end"]) if exp.get("date_end") else None,
                    is_current=exp.get("is_current", False)
                )
                work_experience.append(work_exp)
            
            # Образование
            education = []
            for edu in data.get("education", []):
                edu_item = EducationBase(
                    institution=edu.get("name", ""),
                    faculty=edu.get("faculty"),
                    specialization=edu.get("specialty"),
                    end_year=edu.get("year_end")
                )
                education.append(edu_item)
            
            return ParsedResume(
                source=self.source,
                external_id=str(data.get("id", "")),
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                birth_date=birth_date,
                city=city,
                position_title=position_title,
                desired_salary=desired_salary,
                total_experience_months=total_experience_months,
                work_experience=work_experience,
                education=education,
                skills_raw=[],  # SuperJob не даёт структурированные навыки
                raw_data=data
            )
            
        except Exception as e:
            logger.error(f"[SuperJob] Ошибка парсинга резюме: {e}")
            return None