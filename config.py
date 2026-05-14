"""
Конфигурация приложения
"""
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

# Корень репозитория (каталог, где лежит этот файл) — для SQLite не зависеть от cwd Jupyter/IDE
REPO_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Database (SQLite по умолчанию для разработки)
    DATABASE_URL: str = "sqlite+aiosqlite:///./candidate_scoring.db"
    # Для PostgreSQL: "postgresql+asyncpg://postgres:postgres@localhost:5432/candidate_scoring"
    
    # API Keys
    HH_API_TOKEN: Optional[str] = None
    SUPERJOB_API_KEY: Optional[str] = None
    SUPERJOB_SECRET_KEY: Optional[str] = None
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384
    # Матчинг: 0 = без предфильтра (полный пул и полный скор для каждого).
    # Иначе сначала батч-эмбеддинги всех резюме, отбор top-N по косинусу к вакансии, затем полный скор только для них.
    MATCH_EMBEDDING_PREFILTER_TOP: int = 150
    
    # Cache
    REDIS_URL: Optional[str] = "redis://localhost:6379"
    CACHE_TTL: int = 3600  # 1 hour
    
    # Parsing settings (увеличьте задержку если получаете 429)
    PARSE_DELAY_MIN: float = 2.0
    PARSE_DELAY_MAX: float = 5.0
    MAX_RETRIES: int = 3
    
    # Logging
    LOG_LEVEL: str = "INFO"

    # NER (spaCy EntityRuler по словарю навыков для извлечения сущностей SKILLS)
    NER_ENABLED: bool = True

    # Гибридный ранкер (HGB + bi/cross/TF-IDF). Артефакты: ``artifacts/hybrid_ranker/``
    HYBRID_RANKER_ENABLED: bool = True
    HYBRID_RANKER_DIR: Optional[str] = None  # по умолчанию REPO_ROOT/artifacts/hybrid_ranker
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def sync_database_url() -> str:
    """``DATABASE_URL`` без async-драйвера (для ``create_engine`` и Alembic)."""
    return settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")


def resolved_sync_database_url() -> str:
    """
    URL для синхронного SQLAlchemy: относительный путь в SQLite резолвится от ``REPO_ROOT``,
    а не от ``os.getcwd()`` (иначе ноутбук из ``notebooks/`` открывает другой ``.db``).
    """
    url = sync_database_url()
    if not url.startswith("sqlite"):
        return url
    if ":memory:" in url:
        return url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path_part = url[len(prefix) :]
    if path_part.startswith(":memory"):
        return url
    p = Path(path_part)
    if p.is_absolute():
        return f"sqlite:///{p.resolve().as_posix()}"
    resolved = (REPO_ROOT / path_part).resolve()
    return f"sqlite:///{resolved.as_posix()}"


def resolved_sqlite_database_path() -> Optional[Path]:
    """Если используется файловый SQLite — абсолютный путь к ``.db``; иначе ``None``."""
    u = resolved_sync_database_url()
    if not u.startswith("sqlite:///"):
        return None
    rest = u[len("sqlite:///") :]
    if rest.startswith(":memory"):
        return None
    return Path(rest)


