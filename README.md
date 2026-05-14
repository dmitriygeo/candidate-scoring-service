# Candidate Scoring Service

Веб-сервис для анализа резюме и подбора кандидатов под вакансию.

Сервис помогает загрузить вакансии и резюме, извлечь навыки из текста, сравнить кандидатов с требованиями вакансии и получить ранжированный список наиболее подходящих кандидатов.

## Что умеет сервис

- хранит вакансии, кандидатов, навыки и результаты матчинга;
- загружает вакансии и резюме с HeadHunter;
- извлекает навыки из текста вакансий и резюме;
- нормализует разные написания навыков, например `python3`;
- считает релевантность кандидата вакансии;
- ранжирует кандидатов по итоговому скору;
- предоставляет REST API и веб-интерфейс.

## Стек

Backend:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- sentence-transformers
- scikit-learn

Frontend:

- React
- Vite
- React Router
- TanStack Query
- Axios

## Структура проекта

```text
candidate-scoring-service/
├── app/
│   ├── api/          # API-маршруты
│   ├── data/         # словари и статические данные
│   ├── models/       # SQLAlchemy и Pydantic-модели
│   ├── parsers/      # парсеры вакансий и резюме
│   └── services/     # бизнес-логика
├── alembic/          # миграции базы данных
├── frontend/         # веб-интерфейс
├── config.py         # настройки приложения
├── main.py           # точка входа FastAPI
├── hybrid_ranker.ipynb # jupyter notebook с экспериментами моделей ранжирования
└── requirements.txt  # зависимости


## Основные API-методы

Проверка сервиса:

GET /api/v1/health
GET /api/v1/stats

Вакансии:

GET  /api/v1/vacancies
GET  /api/v1/vacancies/{id}
POST /api/v1/vacancies/analyze

Кандидаты:

GET /api/v1/candidates
GET /api/v1/candidates/{id}

Парсинг HeadHunter:

POST /api/v1/parse/hh/vacancies
POST /api/v1/parse/hh/resumes
POST /api/v1/parse/hh/resume

Матчинг:

POST /api/v1/match/vacancy
GET  /api/v1/match/vacancy/{id}/results
POST /api/v1/match/simple

Навыки:

POST /api/v1/skills/normalize
POST /api/v1/skills/extract
POST /api/v1/skills/ner
GET  /api/v1/skills/groups
GET  /api/v1/skills/coverage

Эмбеддинги:

POST /api/v1/embeddings/encode
POST /api/v1/embeddings/similarity
