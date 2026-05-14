"""Базовый HTTP-парсер: клиент, retry, rate limit."""

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from app.models.schemas import ParsedResume, ParsedVacancy, SourceTypeEnum


T = TypeVar('T')


class BaseParser(ABC, Generic[T]):
    """Общий httpx AsyncClient, задержки и обёртки GET/POST."""
    
    source: SourceTypeEnum
    base_url: str
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[datetime] = None
    
    async def __aenter__(self):
        """Открыть HTTP-клиент."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрыть HTTP-клиент."""
        if self.client:
            await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Заголовки по умолчанию."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }
    
    async def _rate_limit(self):
        """Ограничение частоты запросов"""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            delay = random.uniform(settings.PARSE_DELAY_MIN, settings.PARSE_DELAY_MAX)
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        self._last_request_time = datetime.now()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Запрос с tenacity-retry и rate limit."""
        await self._rate_limit()
        
        logger.debug(f"[{self.source.value}] {method} {url}")
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.warning(f"[{self.source.value}] HTTP {e.response.status_code}: {e.response.text[:200]}")
            raise
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET запрос"""
        return await self._make_request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST запрос"""
        return await self._make_request("POST", url, **kwargs)
    
    @abstractmethod
    async def parse_list(
        self,
        query: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
        **filters
    ) -> List[T]:
        """Список сущностей по запросу (реализуется в подклассе)."""
        pass
    
    @abstractmethod
    async def parse_item(self, item_id: str) -> Optional[T]:
        """Одна сущность по id (реализуется в подклассе)."""
        pass
    
    @staticmethod
    def parse_salary(salary_data: Optional[Dict]) -> tuple:
        """Кортеж (from, to, currency, gross)."""
        if not salary_data:
            return None, None, "RUB", True
        
        return (
            salary_data.get("from"),
            salary_data.get("to"),
            salary_data.get("currency", "RUB"),
            salary_data.get("gross", True)
        )
    
    @staticmethod
    def parse_experience_months(experience_str: Optional[str]) -> Optional[int]:
        """Грубый разбор строки опыта в месяцы (для неструктурированного текста)."""
        if not experience_str:
            return None
        
        experience_str = experience_str.lower()
        
        if "нет опыта" in experience_str or "без опыта" in experience_str:
            return 0
        
        import re
        numbers = re.findall(r'\d+', experience_str)
        
        if not numbers:
            return None
        
        years = int(numbers[0])
        
        if "год" in experience_str or "лет" in experience_str:
            return years * 12
        elif "месяц" in experience_str:
            return years
        
        return years * 12
    
    @staticmethod
    def clean_html(html_text: Optional[str]) -> Optional[str]:
        """Текст без HTML-тегов."""
        if not html_text:
            return None
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.get_text(separator=" ", strip=True)


