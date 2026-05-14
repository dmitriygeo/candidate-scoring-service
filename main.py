"""
Главный файл приложения
Запуск: uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import router
from config import settings

# Настройка логирования
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level=settings.LOG_LEVEL
)

# Создание приложения
app = FastAPI(
    title="Candidate Scoring",
    description="""
    Веб-сервис для автоматического анализа и скоринга кандидатов по резюме
    
    Функционал
    
    Парсинг вакансий - сбор вакансий
    Парсинг резюме - сбор профилей кандидатов из HH
    Извлечение навыков - определение навыков из текста
    Матчинг - расчёт релевантности кандидата для вакансии
    Ранжирование - сортировка кандидатов по скору
    
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    logger.info("Starting Candidate Scoring Service...")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Действия при остановке приложения"""
    logger.info("Shutting down Candidate Scoring Service...")


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "Candidate Scoring",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
