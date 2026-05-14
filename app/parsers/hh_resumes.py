"""Парсер резюме hh.ru (HTML поиск и карточка резюме, без платного API)."""

import re
import json
import asyncio
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseParser
from app.models.schemas import (
    ParsedResume,
    SourceTypeEnum,
    WorkFormatEnum,
    EmploymentTypeEnum,
    WorkExperienceBase,
    EducationBase,
)
from config import settings


class HHResumeParser(BaseParser[ParsedResume]):
    """Поиск и разбор публичных страниц резюме (hh.ru/search/resume)."""
    
    source = SourceTypeEnum.HH
    base_url = "https://hh.ru"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://hh.ru/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
        }
    
    @staticmethod
    def _get_text_by_data_qa(soup: BeautifulSoup, data_qa: str) -> str:
        """Извлекает текст элемента по атрибуту data-qa."""
        el = soup.find(attrs={"data-qa": data_qa})
        return el.get_text(strip=True) if el else ""
    
    @staticmethod
    def _get_all_text_by_data_qa(soup: BeautifulSoup, data_qa: str) -> List[str]:
        """Извлекает тексты всех элементов по атрибуту data-qa."""
        elements = soup.find_all(attrs={"data-qa": data_qa})
        return [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
    
    def _parse_resume_html(self, html: str, url: str) -> Optional[ParsedResume]:
        """Разбор HTML карточки резюме в ``ParsedResume``."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            raw_data = {"url": url}
            
            position_title = self._get_text_by_data_qa(soup, "resume-block-title-position")
            raw_data["desired_position"] = position_title
            
            gender = self._get_text_by_data_qa(soup, "resume-personal-gender")
            raw_data["gender"] = gender
            
            age_text = self._get_text_by_data_qa(soup, "resume-personal-age")
            raw_data["age"] = age_text
            age_years = None
            age_match = re.search(r'(\d+)', age_text)
            if age_match:
                age_years = int(age_match.group(1))
            
            birthday = self._get_text_by_data_qa(soup, "resume-personal-birthday")
            raw_data["birthday"] = birthday
            birth_date = None
            if birthday:
                try:
                    months = {
                        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
                    }
                    date_match = re.search(r'(\d+)\s+(\w+)\s+(\d{4})', birthday)
                    if date_match:
                        day = int(date_match.group(1))
                        month_name = date_match.group(2).lower()
                        year = int(date_match.group(3))
                        if month_name in months:
                            birth_date = datetime(year, months[month_name], day)
                except Exception:
                    pass
            
            city = self._get_text_by_data_qa(soup, "resume-personal-address")
            raw_data["city"] = city
            
            job_status = self._get_text_by_data_qa(soup, "job-search-status")
            raw_data["job_search_status"] = job_status
            is_active_search = "активно" in job_status.lower() if job_status else True
            
            salary_text = self._get_text_by_data_qa(soup, "resume-block-salary")
            raw_data["desired_salary"] = salary_text
            desired_salary = None
            salary_currency = "RUB"
            if salary_text:
                salary_match = re.search(r'([\d\s]+)', salary_text.replace('\xa0', ' '))
                if salary_match:
                    salary_str = salary_match.group(1).replace(' ', '')
                    try:
                        desired_salary = int(salary_str)
                    except Exception:
                        pass
                if '$' in salary_text or 'USD' in salary_text:
                    salary_currency = "USD"
                elif '€' in salary_text or 'EUR' in salary_text:
                    salary_currency = "EUR"
            
            specializations = self._get_all_text_by_data_qa(soup, "resume-block-position-specialization")
            raw_data["specializations"] = specializations
            
            total_experience_months = None
            exp_block = soup.find(attrs={"data-qa": "resume-block-experience"})
            if exp_block:
                exp_title = exp_block.find(class_="resume-block__title-text")
                if exp_title:
                    exp_text = exp_title.get_text(strip=True).replace("Опыт работы", "").strip()
                    raw_data["total_experience"] = exp_text
                    total_experience_months = self._parse_experience_text(exp_text)
            
            work_experience = []
            experience_block = soup.find(attrs={"data-qa": "resume-block-experience"})
            if experience_block:
                exp_positions = experience_block.find_all(attrs={"data-qa": "resume-block-experience-position"})
                
                seen_keys = set()
                
                for pos_el in exp_positions:
                    columns_row = pos_el.find_parent("div", class_="bloko-columns-row")
                    if columns_row:
                        exp_entry = self._parse_experience_row(columns_row)
                        if exp_entry:
                            key = (exp_entry.company, exp_entry.position, str(exp_entry.start_date))
                            if key not in seen_keys:
                                seen_keys.add(key)
                                work_experience.append(exp_entry)
            
            current_employer = None
            if work_experience:
                current_employer = work_experience[0].company
            
            skills_raw = self._extract_skills(soup)
            raw_data["skills"] = skills_raw
            
            education = self._parse_education(soup)
            
            languages = []
            lang_items = soup.find_all(attrs={"data-qa": "resume-block-language-item"})
            for lang in lang_items:
                label = lang.find(class_=re.compile("label--"))
                if label:
                    lang_text = label.get("title") or label.get_text(strip=True)
                    if lang_text:
                        languages.append(lang_text)
            raw_data["languages"] = languages
            
            about = self._get_text_by_data_qa(soup, "resume-block-skills-content")
            raw_data["about"] = about
            
            email = None
            github = None
            telegram = None
            if about:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', about)
                if email_match:
                    email = email_match.group(0)
                    raw_data["email_from_about"] = email
                
                github_match = re.search(r'github\.com/([\w\-]+)', about, re.IGNORECASE)
                if github_match:
                    github = f"https://github.com/{github_match.group(1)}"
                    raw_data["github"] = github
                
                telegram_match = re.search(r'(?:t\.me/|@)([\w_]+)', about)
                if telegram_match:
                    telegram = telegram_match.group(0)
                    raw_data["telegram"] = telegram
            
            external_id = self._extract_resume_id(url)
            
            return ParsedResume(
                source=self.source,
                external_id=external_id,
                profile_url=url,
                first_name=None,
                last_name=None,
                middle_name=None,
                birth_date=birth_date,
                city=city,
                phone=None,
                email=email,
                position_title=position_title,
                about=about,
                desired_salary=desired_salary,
                salary_currency=salary_currency,
                work_format=None,
                total_experience_months=total_experience_months,
                work_experience=work_experience,
                education=education,
                skills_raw=skills_raw,
                raw_data=raw_data
            )
            
        except Exception as e:
            logger.error(f"[HH] Ошибка парсинга HTML резюме: {e}")
            return None
    
    def _parse_experience_text(self, text: str) -> Optional[int]:
        """Парсит текст опыта работы в месяцы."""
        if not text:
            return None
        
        total_months = 0
        
        years_match = re.search(r'(\d+)\s*(?:год|года|лет)', text)
        if years_match:
            total_months += int(years_match.group(1)) * 12
        
        months_match = re.search(r'(\d+)\s*(?:месяц|месяца|месяцев)', text)
        if months_match:
            total_months += int(months_match.group(1))
        
        return total_months if total_months > 0 else None
    
    def _parse_experience_row(self, row) -> Optional[WorkExperienceBase]:
        """Одна строка блока опыта (``bloko-columns-row``) → ``WorkExperienceBase``."""
        try:
            period_col = row.find("div", class_=re.compile(r"bloko-column_l-2|bloko-column_s-2|bloko-column_m-2"))
            
            start_date = None
            end_date = None
            is_current = False
            duration_months = None
            
            if period_col:
                period_text = ""
                for node in period_col.children:
                    if isinstance(node, str):
                        period_text += node
                    elif node.name == "span":
                        period_text += node.get_text(" ", strip=True) + " "
                
                dates = self._parse_period_text(period_text)
                start_date = dates.get("start")
                end_date = dates.get("end")
                is_current = dates.get("is_current", False)
                
                duration_div = period_col.find("div", class_="bloko-text_tertiary")
                if duration_div:
                    duration_text = duration_div.get_text(strip=True)
                    duration_months = self._parse_duration_text(duration_text)
            
            details_col = row.find("div", class_=re.compile(r"bloko-column_l-10|bloko-column_s-6|bloko-column_m-7"))
            
            company = ""
            position = ""
            description = ""
            
            if details_col:
                container = details_col.find("div", class_="resume-block-container")
                if container:
                    company_el = container.find("div", class_="bloko-text_strong")
                    if company_el:
                        link = company_el.find("a")
                        if link:
                            company = link.get_text(strip=True)
                        else:
                            company = company_el.get_text(strip=True)
                    
                    position_el = container.find(attrs={"data-qa": "resume-block-experience-position"})
                    if position_el:
                        position = position_el.get_text(strip=True)
                    
                    description_el = container.find(attrs={"data-qa": "resume-block-experience-description"})
                    if description_el:
                        description = description_el.get_text("\n", strip=True)
            
            if not company and not position:
                return None
            
            return WorkExperienceBase(
                company=company or "Не указано",
                position=position or "Не указано",
                description=description if description else None,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                duration_months=duration_months
            )
            
        except Exception as e:
            logger.debug(f"[HH] Ошибка парсинга опыта работы: {e}")
            return None
    
    def _parse_duration_text(self, text: str) -> Optional[int]:
        """
        Парсит текст продолжительности работы.
        Пример: "1 год 6 месяцев" -> 18
        """
        if not text:
            return None
        
        total_months = 0
        
        years_match = re.search(r'(\d+)\s*(?:год|года|лет)', text)
        if years_match:
            total_months += int(years_match.group(1)) * 12
        
        months_match = re.search(r'(\d+)\s*(?:месяц|месяца|месяцев)', text)
        if months_match:
            total_months += int(months_match.group(1))
        
        return total_months if total_months > 0 else None
    
    def _parse_experience_item(self, item) -> Optional[WorkExperienceBase]:
        """Устаревший метод для обратной совместимости."""
        parent_row = item.find_parent(class_="bloko-columns-row")
        if parent_row:
            return self._parse_experience_row(parent_row)
        return None
    
    def _parse_period_text(self, text: str) -> Dict[str, Any]:
        """Парсит период работы из текста."""
        result = {"start": None, "end": None, "is_current": False}
        
        if not text:
            return result
        
        months_map = {
            'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4,
            'май': 5, 'июнь': 6, 'июль': 7, 'август': 8,
            'сентябрь': 9, 'октябрь': 10, 'ноябрь': 11, 'декабрь': 12
        }
        
        dates = re.findall(r'(\w+)\s+(\d{4})', text.lower())
        
        if len(dates) >= 1:
            month_name, year = dates[0]
            month = months_map.get(month_name, 1)
            try:
                result["start"] = datetime(int(year), month, 1)
            except Exception:
                pass
        
        if len(dates) >= 2:
            month_name, year = dates[1]
            month = months_map.get(month_name, 1)
            try:
                result["end"] = datetime(int(year), month, 1)
            except Exception:
                pass
        
        if "настоящее время" in text.lower() or "по настоящее" in text.lower():
            result["is_current"] = True
            result["end"] = None
        
        return result
    
    def _extract_skills(self, soup: BeautifulSoup) -> List[str]:
        """Извлекает навыки из HTML."""
        skills = []
        
        skill_tags = soup.select('[data-qa="bloko-tag__text"] .label--_PWdo2ImNdEM1M0A')
        if skill_tags:
            skills = [tag.get("title") or tag.get_text(strip=True) for tag in skill_tags]
        
        if not skills:
            skill_tags = soup.select('[data-qa="bloko-tag__text"]')
            for tag in skill_tags:
                parent = tag.find_parent(attrs={"data-qa": "resume-block-languages"})
                if parent:
                    continue
                
                label = tag.find(class_=re.compile("label--"))
                if label:
                    skill_text = label.get("title") or label.get_text(strip=True)
                    if skill_text:
                        skills.append(skill_text)
        
        skills = list(dict.fromkeys(skills))
        skills = [s for s in skills if "—" not in s and s]
        
        return skills
    
    def _parse_education(self, soup: BeautifulSoup) -> List[EducationBase]:
        """Парсит образование."""
        education = []
        edu_block = soup.find(attrs={"data-qa": "resume-block-education"})
        
        if not edu_block:
            return education
        
        edu_items = edu_block.find_all(attrs={"data-qa": "resume-block-education-item"})
        
        for item in edu_items:
            try:
                edu_entry = {}
                
                parent_row = item.find_parent(class_="bloko-columns-row")
                end_year = None
                degree = None
                
                if parent_row:
                    year_col = parent_row.find(class_="bloko-column_l-2")
                    if year_col:
                        year_text = year_col.get_text(strip=True)
                        year_match = re.search(r'(\d{4})', year_text)
                        if year_match:
                            end_year = int(year_match.group(1))
                        
                        if 'Бакалавр' in year_text:
                            degree = 'bachelor'
                        elif 'Магистр' in year_text:
                            degree = 'master'
                        elif 'Специалист' in year_text:
                            degree = 'specialist'
                        elif 'Аспирант' in year_text or 'PhD' in year_text:
                            degree = 'phd'
                
                name_el = item.find(attrs={"data-qa": "resume-block-education-name"})
                institution = name_el.get_text(strip=True) if name_el else "Не указано"
                
                org_el = item.find(attrs={"data-qa": "resume-block-education-organization"})
                faculty_spec = org_el.get_text(strip=True) if org_el else None
                
                education.append(EducationBase(
                    institution=institution,
                    faculty=faculty_spec,
                    specialization=None,
                    degree=degree,
                    end_year=end_year
                ))
                
            except Exception as e:
                logger.debug(f"[HH] Ошибка парсинга образования: {e}")
                continue
        
        return education
    
    @staticmethod
    def _extract_resume_id(url: str) -> str:
        """Извлекает ID резюме из URL."""
        match = re.search(r'/resume/([a-f0-9]+)', url)
        return match.group(1) if match else url.split("/")[-1].split("?")[0]
    
    def _extract_resume_links_from_search(self, html: str) -> List[str]:
        """Извлекает ссылки на резюме со страницы поиска."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        resume_links = soup.find_all("a", href=re.compile(r"/resume/[a-f0-9]{20,}"))
        
        for link in resume_links:
            href = link.get("href", "")
            if href:
                if "/advanced" in href or "/search" in href:
                    continue
                    
                if href.startswith("/"):
                    href = urljoin(self.base_url, href)
                clean_url = href.split("?")[0]
                if clean_url not in links:
                    links.append(clean_url)
        
        return links
    
    def _get_total_pages_and_count(self, html: str) -> tuple:
        """Определяет общее количество страниц и резюме."""
        soup = BeautifulSoup(html, "html.parser")
        total_resumes = 0
        total_pages = 1
        
        text = soup.get_text()
        match = re.search(r'Найдено\s+([\d\s\xa0]+)\s*резюме', text)
        if match:
            total_str = match.group(1).replace(' ', '').replace('\xa0', '')
            total_resumes = int(total_str)
        
        pager_items = soup.select('[data-qa="pager-page"]')
        if pager_items:
            pages = []
            for p in pager_items:
                page_text = p.get_text(strip=True)
                if page_text.isdigit():
                    pages.append(int(page_text))
            if pages:
                total_pages = max(pages)
        elif total_resumes > 0:
            total_pages = min((total_resumes + 49) // 50, 40)
        
        return total_pages, total_resumes
    
    async def parse_list(
        self,
        query: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
        area: Optional[int] = None,
        experience: Optional[str] = None,
        search_field: str = "title",
        logic: str = "normal",
        **filters
    ) -> List[ParsedResume]:
        """Поиск резюме на HH (скрейпинг); ``search_field``: title или everywhere; ``logic``: normal, any, phrase."""
        params = {
            "page": page,
            "pos": "full_text",
            "exp_period": "all_time",
            "order_by": "relevance",
        }
        
        if query:
            params["text"] = query
            params["logic"] = logic
            
            if search_field == "title":
                params["pos"] = "position"
            elif search_field == "everywhere":
                params["pos"] = "full_text"
            
        if area:
            params["area"] = area
        if experience:
            params["experience"] = experience
        
        search_url = f"{self.base_url}/search/resume?{urlencode(params)}"
        logger.info(f"[HH] URL поиска резюме: {search_url}")
        
        try:
            response = await self.get(search_url)
            html = response.text
            
            resume_urls = self._extract_resume_links_from_search(html)
            total_pages, total_resumes = self._get_total_pages_and_count(html)
            
            logger.info(f"[HH] Найдено резюме: {total_resumes}, страниц: {total_pages}, ссылок на странице: {len(resume_urls)}")
            
            resume_urls = resume_urls[:per_page]
            
            resumes = []
            query_lower = query.lower() if query else ""
            
            for i, url in enumerate(resume_urls, 1):
                logger.debug(f"[HH] Парсим резюме {i}/{len(resume_urls)}: {url}")
                
                try:
                    await self._rate_limit()
                    resume_response = await self.get(url)
                    resume = self._parse_resume_html(resume_response.text, url)
                    
                    if resume:
                        if query and search_field == "title" and resume.position_title:
                            position_lower = resume.position_title.lower()
                            query_words = query_lower.split()
                            
                            if logic == "phrase":
                                if query_lower in position_lower:
                                    resumes.append(resume)
                                    logger.debug(f"[HH] Резюме соответствует запросу: {resume.position_title}")
                                else:
                                    logger.debug(f"[HH] Пропущено (не содержит фразу): {resume.position_title}")
                            else:
                                if any(word in position_lower for word in query_words):
                                    resumes.append(resume)
                                    logger.debug(f"[HH] Резюме соответствует запросу: {resume.position_title}")
                                else:
                                    logger.debug(f"[HH] Пропущено (не соответствует): {resume.position_title}")
                        else:
                            resumes.append(resume)
                            
                except Exception as e:
                    logger.error(f"[HH] Ошибка парсинга резюме {url}: {e}")
                    continue
            
            logger.info(f"[HH] После фильтрации: {len(resumes)} резюме соответствуют запросу")
            return resumes
            
        except Exception as e:
            logger.error(f"[HH] Ошибка парсинга списка резюме: {e}")
            return []
    
    async def parse_item(self, item_id: str) -> Optional[ParsedResume]:
        """Одно резюме по id или полному URL."""
        if item_id.startswith("http"):
            url = item_id
        else:
            url = f"{self.base_url}/resume/{item_id}"
        
        try:
            response = await self.get(url)
            return self._parse_resume_html(response.text, url)
        except Exception as e:
            logger.error(f"[HH] Ошибка парсинга резюме {item_id}: {e}")
            return None
    
    async def collect_resume_urls(
        self,
        search_url: str,
        max_pages: int = 10
    ) -> List[str]:
        """
        Собирает ссылки на резюме со страниц поиска.
        
        Args:
            search_url: URL страницы поиска (с параметрами)
            max_pages: Максимальное количество страниц для парсинга
            
        Returns:
            Список уникальных URL резюме
        """
        all_urls = []
        
        parsed = urlparse(search_url)
        base_params = parse_qs(parsed.query)
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v 
                  for k, v in base_params.items()}
        
        logger.info(f"[HH] Загружаем страницу поиска: {search_url[:70]}...")
        
        try:
            response = await self.get(search_url)
            html = response.text
        except Exception as e:
            logger.error(f"[HH] Ошибка загрузки страницы поиска: {e}")
            return []
        
        urls = self._extract_resume_links_from_search(html)
        all_urls.extend(urls)
        
        total_pages, total_resumes = self._get_total_pages_and_count(html)
        pages_to_parse = min(total_pages, max_pages)
        
        logger.info(f"[HH] Найдено резюме: {total_resumes}, страниц: {total_pages}, парсим: {pages_to_parse}")
        
        for page in range(1, pages_to_parse):
            params["page"] = str(page)
            page_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(params, doseq=True)}"
            
            logger.info(f"[HH] Страница {page + 1}/{pages_to_parse}...")
            
            try:
                await self._rate_limit()
                response = await self.get(page_url)
                urls = self._extract_resume_links_from_search(response.text)
                all_urls.extend(urls)
                logger.debug(f"[HH] Найдено ссылок: {len(urls)}")
            except Exception as e:
                logger.error(f"[HH] Ошибка на странице {page + 1}: {e}")
                continue
        
        unique_urls = list(dict.fromkeys(all_urls))
        logger.info(f"[HH] Всего уникальных ссылок: {len(unique_urls)}")
        
        return unique_urls
    
    async def parse_resumes_batch(
        self,
        urls: List[str],
        max_count: Optional[int] = None
    ) -> List[ParsedResume]:
        """
        Парсит пакет резюме по списку URL.
        
        Args:
            urls: Список URL резюме
            max_count: Максимальное количество для парсинга
            
        Returns:
            Список распарсенных резюме
        """
        if max_count:
            urls = urls[:max_count]
        
        resumes = []
        total = len(urls)
        
        for i, url in enumerate(urls, 1):
            logger.info(f"[HH] [{i}/{total}] Парсим: {url}")
            
            try:
                await self._rate_limit()
                resume = await self.parse_item(url)
                if resume:
                    resumes.append(resume)
            except Exception as e:
                logger.error(f"[HH] Ошибка парсинга {url}: {e}")
                continue
        
        logger.info(f"[HH] Спарсено резюме: {len(resumes)}")
        return resumes
    
    async def search_by_specialization(
        self,
        specialization: str,
        area: int = 113,
        max_pages: int = 3,
        per_page: int = 20
    ) -> List[ParsedResume]:
        """
        Поиск резюме по специализации.
        
        Args:
            specialization: Название специализации
            area: Регион (113 = Россия)
            max_pages: Количество страниц для парсинга
            per_page: Резюме на странице
        """
        specialization_queries = {
            "backend": "backend разработчик OR python developer",
            "frontend": "frontend разработчик OR react developer",
            "fullstack": "fullstack developer OR full stack разработчик",
            "data_science": "data scientist OR аналитик данных",
            "devops": "devops engineer OR SRE",
            "qa": "QA engineer OR тестировщик",
            "mobile": "mobile developer OR iOS разработчик OR android разработчик",
        }
        
        query = specialization_queries.get(specialization, specialization)
        
        all_resumes = []
        for page in range(max_pages):
            resumes = await self.parse_list(
                query=query,
                area=area,
                page=page,
                per_page=per_page
            )
            all_resumes.extend(resumes)
            
            if len(resumes) < per_page:
                break
        
        return all_resumes
