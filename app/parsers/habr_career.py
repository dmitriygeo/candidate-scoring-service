"""Хабр Карьера: вакансии и резюме через HTML (публичного API нет)."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re
import json

from bs4 import BeautifulSoup
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


class HabrCareerParser(BaseParser[ParsedVacancy]):
    """Скрапинг career.habr.com (соблюдать rate limit и robots.txt)."""
    
    source = SourceTypeEnum.HABR_CAREER
    base_url = "https://career.habr.com"
    
    def _get_headers(self) -> Dict[str, str]:
        headers = super()._get_headers()
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        return headers
    
    async def parse_list(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
        city: Optional[str] = None,
        remote: bool = False,
        qualification: Optional[int] = None,
        specializations: Optional[List[int]] = None,
        skills: Optional[List[int]] = None,
        **filters
    ) -> List[ParsedVacancy]:
        """Список вакансий; нумерация страниц с 1, как на сайте."""
        params = {"page": page}
        
        if query:
            params["q"] = query
        if city:
            params["city"] = city
        if remote:
            params["remote"] = "true"
        if qualification:
            params["qid"] = qualification
        if specializations:
            params["s[]"] = specializations
        if skills:
            params["skills[]"] = skills
        
        try:
            response = await self.get(f"{self.base_url}/vacancies", params=params)
            html = response.text
            
            vacancies = self._parse_vacancy_list_html(html)
            logger.info(f"[Habr] Найдено вакансий на странице: {len(vacancies)}")
            
            return vacancies
            
        except Exception as e:
            logger.error(f"[Habr] Ошибка парсинга списка вакансий: {e}")
            return []
    
    async def parse_item(self, item_id: str) -> Optional[ParsedVacancy]:
        """Карточка вакансии по id или slug."""
        try:
            url = f"{self.base_url}/vacancies/{item_id}"
            response = await self.get(url)
            html = response.text
            
            return self._parse_vacancy_detail_html(html, item_id)
            
        except Exception as e:
            logger.error(f"[Habr] Ошибка парсинга вакансии {item_id}: {e}")
            return None
    
    def _parse_vacancy_list_html(self, html: str) -> List[ParsedVacancy]:
        """HTML списка → список ``ParsedVacancy``."""
        soup = BeautifulSoup(html, "lxml")
        vacancies = []
        
        vacancy_cards = soup.select(".vacancy-card")
        
        for card in vacancy_cards:
            try:
                vacancy = self._parse_vacancy_card(card)
                if vacancy:
                    vacancies.append(vacancy)
            except Exception as e:
                logger.debug(f"[Habr] Ошибка парсинга карточки: {e}")
                continue
        
        return vacancies
    
    def _parse_vacancy_card(self, card: BeautifulSoup) -> Optional[ParsedVacancy]:
        """Одна карточка из списка вакансий."""
        try:
            title_link = card.select_one(".vacancy-card__title-link")
            if not title_link:
                return None
            
            href = title_link.get("href", "")
            external_id = href.split("/")[-1] if href else ""
            title = title_link.get_text(strip=True)
            
            company_elem = card.select_one(".vacancy-card__company-title")
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            salary_elem = card.select_one(".vacancy-card__salary")
            salary_from, salary_to, currency = self._parse_habr_salary(
                salary_elem.get_text(strip=True) if salary_elem else None
            )
            
            location_elem = card.select_one(".vacancy-card__meta")
            city = None
            work_format = None
            
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                if "Удалённо" in location_text or "Remote" in location_text:
                    work_format = WorkFormatEnum.REMOTE
                city_match = re.search(r'(Москва|Санкт-Петербург|[А-Яа-я]+)', location_text)
                if city_match:
                    city = city_match.group(1)
            
            skills_raw = []
            skills_elems = card.select(".vacancy-card__skills .preserve-line")
            for skill_elem in skills_elems:
                skill_text = skill_elem.get_text(strip=True)
                if skill_text:
                    skills_raw.append(skill_text)
            
            return ParsedVacancy(
                source=self.source,
                external_id=external_id,
                source_url=f"{self.base_url}{href}" if href else None,
                title=title,
                company=company,
                description=None,
                salary_from=salary_from,
                salary_to=salary_to,
                salary_currency=currency,
                city=city,
                work_format=work_format,
                skills_raw=skills_raw,
            )
            
        except Exception as e:
            logger.debug(f"[Habr] Ошибка парсинга карточки: {e}")
            return None
    
    def _parse_vacancy_detail_html(
        self,
        html: str,
        item_id: str
    ) -> Optional[ParsedVacancy]:
        """HTML страницы вакансии → ``ParsedVacancy``."""
        soup = BeautifulSoup(html, "lxml")
        
        try:
            title_elem = soup.select_one(".vacancy-page__title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            company_elem = soup.select_one(".vacancy-page__company-title")
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            salary_elem = soup.select_one(".vacancy-page__salary")
            salary_from, salary_to, currency = self._parse_habr_salary(
                salary_elem.get_text(strip=True) if salary_elem else None
            )
            
            description_elem = soup.select_one(".vacancy-page__description")
            description = description_elem.get_text(separator="\n", strip=True) if description_elem else None
            
            skills_raw = []
            skills_container = soup.select_one(".vacancy-page__skills")
            if skills_container:
                for skill_elem in skills_container.select(".preserve-line"):
                    skill_text = skill_elem.get_text(strip=True)
                    if skill_text:
                        skills_raw.append(skill_text)
            
            city = None
            work_format = None
            
            meta_items = soup.select(".vacancy-page__info-item")
            for item in meta_items:
                text = item.get_text(strip=True)
                if "Удалённо" in text or "Remote" in text:
                    work_format = WorkFormatEnum.REMOTE
                elif "Офис" in text:
                    work_format = WorkFormatEnum.OFFICE
                elif "Гибрид" in text:
                    work_format = WorkFormatEnum.HYBRID
            
            experience_months = None
            for item in meta_items:
                text = item.get_text(strip=True)
                exp_match = re.search(r'(\d+)\s*(?:год|лет|года)', text)
                if exp_match:
                    experience_months = int(exp_match.group(1)) * 12
                    break
            
            return ParsedVacancy(
                source=self.source,
                external_id=item_id,
                source_url=f"{self.base_url}/vacancies/{item_id}",
                title=title,
                company=company,
                description=description,
                salary_from=salary_from,
                salary_to=salary_to,
                salary_currency=currency,
                experience_from=experience_months,
                city=city,
                work_format=work_format,
                skills_raw=skills_raw,
            )
            
        except Exception as e:
            logger.error(f"[Habr] Ошибка парсинга детальной страницы: {e}")
            return None
    
    @staticmethod
    def _parse_habr_salary(salary_text: Optional[str]) -> tuple:
        """Строка зарплаты с Хабра → (from, to, currency)."""
        if not salary_text:
            return None, None, "RUB"
        
        currency = "RUB"
        if "$" in salary_text:
            currency = "USD"
        elif "€" in salary_text:
            currency = "EUR"
        
        numbers = re.findall(r'[\d\s]+', salary_text)
        numbers = [int(n.replace(" ", "").replace("\u00a0", "")) for n in numbers if n.strip()]
        
        salary_from = None
        salary_to = None
        
        if len(numbers) >= 2:
            salary_from = numbers[0]
            salary_to = numbers[1]
        elif len(numbers) == 1:
            if "от" in salary_text.lower():
                salary_from = numbers[0]
            elif "до" in salary_text.lower():
                salary_to = numbers[0]
            else:
                salary_from = numbers[0]
        
        return salary_from, salary_to, currency
    
    async def search_specialists(
        self,
        query: Optional[str] = None,
        page: int = 1,
        skills: Optional[List[str]] = None,
        **filters
    ) -> List[ParsedResume]:
        """Поиск специалистов (HTML /resumes)."""
        params = {"page": page}
        
        if query:
            params["q"] = query
        if skills:
            params["skills[]"] = skills
        
        try:
            response = await self.get(f"{self.base_url}/resumes", params=params)
            html = response.text
            
            return self._parse_resume_list_html(html)
            
        except Exception as e:
            logger.error(f"[Habr] Ошибка поиска специалистов: {e}")
            return []
    
    def _parse_resume_list_html(self, html: str) -> List[ParsedResume]:
        """HTML списка резюме."""
        soup = BeautifulSoup(html, "lxml")
        resumes = []
        
        cards = soup.select(".resume-card")
        
        for card in cards:
            try:
                resume = self._parse_resume_card(card)
                if resume:
                    resumes.append(resume)
            except Exception as e:
                logger.debug(f"[Habr] Ошибка парсинга карточки резюме: {e}")
                continue
        
        return resumes
    
    def _parse_resume_card(self, card: BeautifulSoup) -> Optional[ParsedResume]:
        """Одна карточка специалиста."""
        try:
            link_elem = card.select_one(".resume-card__title-link")
            if not link_elem:
                return None
            
            href = link_elem.get("href", "")
            external_id = href.split("/")[-1] if href else ""
            
            name_text = link_elem.get_text(strip=True)
            name_parts = name_text.split()
            first_name = name_parts[0] if name_parts else None
            last_name = name_parts[1] if len(name_parts) > 1 else None
            
            position_elem = card.select_one(".resume-card__specialization")
            position_title = position_elem.get_text(strip=True) if position_elem else None
            
            skills_raw = []
            skills_elems = card.select(".resume-card__skills .preserve-line")
            for skill_elem in skills_elems:
                skill_text = skill_elem.get_text(strip=True)
                if skill_text:
                    skills_raw.append(skill_text)
            
            return ParsedResume(
                source=self.source,
                external_id=external_id,
                profile_url=f"{self.base_url}{href}" if href else None,
                first_name=first_name,
                last_name=last_name,
                position_title=position_title,
                skills_raw=skills_raw,
            )
            
        except Exception as e:
            logger.debug(f"[Habr] Ошибка парсинга карточки резюме: {e}")
            return None


