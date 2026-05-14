# Candidate Scoring Service

Веб-сервис для автоматического анализа и скоринга кандидатов на работу по резюме и агрегированным данным из различных источников.

## Чекпоинт 2: Baseline

### Реализованные компоненты

#### 1. Схема данных

- **SQLAlchemy модели** (`app/models/database.py`):
  - `Candidate` - профиль кандидата
  - `CandidateProfile` - данные из конкретного источника
  - `Vacancy` - вакансия
  - `Skill` - навык/технология
  - `SkillGroup` - группа навыков
  - `CandidateSkill`, `VacancySkill` - связи навыков
  - `Education` - образование
  - `WorkExperience` - опыт работы
  - `CandidateVacancyMatch` - результат матчинга

- **Pydantic схемы** (`app/models/schemas.py`):
  - Валидация входных данных
  - Сериализация ответов API
  - Схемы для парсинга

#### 2. Парсеры данных

- **HeadHunter** (`app/parsers/hh_vacancies.py`, `hh_resumes.py`):
  - Поиск и парсинг вакансий через API
  - Получение детальной информации о вакансии
  - Парсинг резюме (требует авторизацию)

- **SuperJob** (`app/parsers/superjob.py`):
  - Парсинг вакансий через API
  - Парсинг резюме (требует OAuth)

- **Хабр Карьера** (`app/parsers/habr_career.py`):
  - Веб-скрапинг вакансий
  - Поиск специалистов

- **LinkedIn** (`app/parsers/linkedin.py`):
  - Парсинг экспортированных данных
  - Базовый скрапинг публичных профилей

#### 3. Словарь навыков

- **JSON словарь** (`app/data/skills_dictionary.json`):
  - 250+ IT навыков
  - Группировка по специализациям (backend, frontend, DS, DE, DevOps, mobile, QA)
  - Алиасы для различных написаний

- **Сервис навыков** (`app/services/skills.py`):
  - Нормализация навыков
  - Определение специализации по навыкам
  - Расчёт покрытия навыков

#### 4. Эмбеддинги

- **Сервис эмбеддингов** (`app/services/embeddings.py`):
  - Генерация эмбеддингов через sentence-transformers
  - Мультиязычная модель (русский + английский)
  - Кэширование эмбеддингов
  - FAISS индекс для быстрого поиска

#### 5. Матчинг и ранжирование

- **Сервис матчинга** (`app/services/matching.py`):
  - Расчёт скора релевантности кандидата вакансии
  - Компоненты скора: навыки, опыт, образование, зарплата, локация, эмбеддинги
  - Настраиваемые веса компонентов
  - Детальная разбивка скора

- **Ранжирование кандидатов**:
  - Сортировка по интегральному скору
  - Быстрый предварительный отбор по эмбеддингам

- **Hybrid HGB** (если в каталоге `artifacts/hybrid_ranker/` есть `metadata.json`, `tfidf.joblib`, `hgb.joblib`):
  - Bi-encoder `intfloat/multilingual-e5-base`, cross-encoder `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, TF-IDF и `HistGradientBoostingClassifier`
  - При ранжировании `total_score` заменяется вероятностью гибридной модели; прежний взвешенный скор сохраняется в `score_details.heuristic_total_score`
  - Обучение: `python scripts/train_hybrid_hgb.py --data-dir <путь_к_csv> --out-dir artifacts/hybrid_ranker`
  - Переменные окружения: `HYBRID_RANKER_ENABLED`, `HYBRID_RANKER_DIR` (см. `config.py`)

#### 6. Извлечение навыков

- **Экстрактор навыков** (`app/services/skill_extractor.py`):
  - Извлечение навыков из текста вакансий и резюме
  - Определение уровня владения навыком
  - Агрегация навыков из разных источников

## Установка

```bash
# Клонирование репозитория
cd C:\VKR\baseline2

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Скачивание модели для эмбеддингов (автоматически при первом использовании)
# Модель: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## Настройка базы данных

По умолчанию используется **SQLite** (файл `candidate_scoring.db` создаётся автоматически).

```bash
# Применение миграций (создаст таблицы)
alembic upgrade head
```

Для использования **PostgreSQL**:
1. Установите PostgreSQL
2. Создайте базу: `createdb candidate_scoring`
3. Измените `DATABASE_URL` в `config.py` или создайте `.env` файл

## Запуск

### API сервер

```bash
uvicorn main:app --reload --port 8000
```

API документация: http://localhost:8000/docs

### Демонстрация

```bash
python examples/demo.py
```

### Тесты

```bash
pytest tests/ -v
```

## API Endpoints

### Статистика и здоровье
- `GET /api/v1/stats` - статистика базы данных
- `GET /api/v1/health` - проверка здоровья сервиса

### Вакансии
- `GET /api/v1/vacancies` - список вакансий из БД
- `GET /api/v1/vacancies/{id}` - вакансия по ID
- `POST /api/v1/vacancies/analyze` - анализ текста вакансии

### Кандидаты
- `GET /api/v1/candidates` - список кандидатов из БД
- `GET /api/v1/candidates/{id}` - кандидат по ID

### Парсинг
- `POST /api/v1/parse/hh/vacancies` - парсинг вакансий с HH.ru и сохранение в БД
- `POST /api/v1/parse/hh/resumes` - парсинг резюме с HH.ru (веб-скрейпинг) и сохранение в БД
- `POST /api/v1/parse/hh/resume` - парсинг одного резюме по URL

### Матчинг
- `POST /api/v1/match/vacancy` - найти кандидатов для вакансии (с сохранением в БД)
- `GET /api/v1/match/vacancy/{id}/results` - получить сохранённые результаты матчинга
- `POST /api/v1/match/simple` - простой матчинг без БД

### Навыки
- `POST /api/v1/skills/normalize` - нормализация списка навыков
- `POST /api/v1/skills/extract` - извлечение навыков из текста
- `GET /api/v1/skills/groups` - получение групп навыков
- `GET /api/v1/skills/coverage` - расчёт покрытия навыков

### Эмбеддинги
- `POST /api/v1/embeddings/encode` - генерация эмбеддингов
- `POST /api/v1/embeddings/similarity` - поиск похожих текстов

## Пример использования

```python
from app.services.skills import SkillsService
from app.services.embeddings import EmbeddingService
from app.services.matching import MatchingService

# Нормализация навыков
skills_service = SkillsService()
normalized = skills_service.normalize_skills(["python3", "js", "k8s"])
# ['Python', 'JavaScript', 'Kubernetes']

# Определение специализации
spec = skills_service.detect_specialization(["Python", "Django", "PostgreSQL"])
# SpecializationGroupEnum.BACKEND

# Расчёт покрытия навыков
coverage = skills_service.calculate_skills_coverage(
    candidate_skills=["Python", "Django"],
    required_skills=["Python", "Django", "PostgreSQL"]
)
# {'required_coverage': 0.67, ...}

# Поиск по эмбеддингам
embedding_service = EmbeddingService()
results = embedding_service.find_most_similar(
    query="Python backend разработчик",
    candidates=["Senior Python Developer", "Frontend React Developer"],
    top_k=5
)
```

## Структура проекта

```
baseline2/
├── app/
│   ├── api/             # API маршруты
│   ├── data/            # Словари и статические данные
│   ├── models/          # SQLAlchemy и Pydantic модели
│   ├── parsers/         # Парсеры источников данных
│   └── services/        # Бизнес-логика
├── alembic/             # Миграции БД
├── examples/            # Примеры использования
├── tests/               # Тесты
├── config.py            # Конфигурация
├── main.py              # Точка входа FastAPI
└── requirements.txt     # Зависимости
```

---

## 🖥️ Frontend (Web-интерфейс)

### Установка и запуск

```bash
# 1. Убедитесь, что Node.js установлен
node --version  # Должен быть v18+

# 2. Перейдите в папку frontend
cd frontend

# 3. Установите зависимости
npm install

# 4. Запустите dev-сервер
npm run dev
```

Откройте http://localhost:3000

### Требования

- **Node.js 18+** - [скачать](https://nodejs.org/)
- **Backend запущен** на http://localhost:8000

---

## 🧪 Инструкция по тестированию

### Шаг 1: Запуск Backend

```bash
# Терминал 1: Backend
cd C:\VKR\baseline2
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Проверьте: http://localhost:8000/docs

### Шаг 2: Запуск Frontend

```bash
# Терминал 2: Frontend
cd C:\VKR\baseline2\frontend
npm install
npm run dev
```

Откройте: http://localhost:3000

### Шаг 3: Тестирование функционала

#### 3.1 Парсинг вакансий

1. Перейдите на страницу **"Парсер HH"** (`/parser`)
2. Выберите **"Вакансии"**
3. Введите запрос: `Python developer`
4. Нажмите **"Спарсить вакансии"**
5. Дождитесь результатов (30-60 сек)
6. Проверьте количество сохранённых вакансий

#### 3.2 Парсинг резюме

1. На странице **"Парсер HH"** выберите **"Резюме"**
2. Введите запрос: `Data Scientist`
3. Выберите "В заголовке резюме"
4. Нажмите **"Спарсить резюме"**
5. Дождитесь результатов

#### 3.3 Просмотр вакансий

1. Перейдите на **"Вакансии"** (`/vacancies`)
2. Просмотрите список загруженных вакансий
3. Нажмите на вакансию для просмотра деталей
4. Проверьте навыки, зарплату, описание

#### 3.4 Просмотр кандидатов

1. Перейдите на **"Кандидаты"** (`/candidates`)
2. Просмотрите список загруженных резюме
3. Нажмите на кандидата для просмотра деталей
4. Проверьте опыт работы, образование, навыки

#### 3.5 Матчинг

1. На странице **"Вакансии"** выберите вакансию
2. Нажмите **"Найти кандидатов"**
3. На странице матчинга настройте минимальный скор
4. Нажмите **"Запустить матчинг"**
5. Просмотрите ранжированный список кандидатов
6. Проверьте детали скора (навыки, опыт, семантика)

#### 3.6 Анализ навыков

1. Перейдите на **"Анализ навыков"** (`/skills`)
2. **Нормализация**: введите `python3, питон, numpy, sklearn`
3. Нажмите "Нормализовать" и проверьте результаты
4. **Извлечение**: вставьте текст вакансии
5. Нажмите "Извлечь навыки" и проверьте результаты

---

## 📊 Тестирование API напрямую

### Через Swagger UI

Откройте http://localhost:8000/docs и протестируйте эндпоинты.

### Через curl (PowerShell)

```powershell
# Статистика
curl.exe http://localhost:8000/api/v1/stats

# Парсинг вакансий
curl.exe -X POST "http://localhost:8000/api/v1/parse/hh/vacancies" `
  -H "Content-Type: application/json" `
  -d '{"query": "Python developer", "per_page": 5}'

# Парсинг резюме
curl.exe -X POST "http://localhost:8000/api/v1/parse/hh/resumes" `
  -H "Content-Type: application/json" `
  -d '{"query": "Data Scientist", "per_page": 5, "search_field": "title"}'

# Нормализация навыков
curl.exe -X POST "http://localhost:8000/api/v1/skills/normalize" `
  -H "Content-Type: application/json" `
  -d '{"skills": ["python3", "numpy", "django"]}'

# Матчинг
curl.exe -X POST "http://localhost:8000/api/v1/match/vacancy" `
  -H "Content-Type: application/json" `
  -d '{"vacancy_id": 1, "min_score": 0.3, "limit": 10}'
```

---

## ⚠️ Возможные проблемы

### Backend не запускается

```bash
# Проверьте виртуальное окружение
venv\Scripts\activate

# Переустановите зависимости
pip install -r requirements.txt
```

### Frontend не подключается к API

1. Убедитесь, что backend запущен на порту 8000
2. Проверьте файл `frontend/.env`:
   ```
   VITE_API_URL=http://localhost:8000/api/v1
   ```
3. Проверьте CORS в `main.py`

### Парсинг возвращает ошибки

- **429 Too Many Requests** — подождите 5-10 минут
- Увеличьте задержку в `config.py`:
  ```python
  PARSE_DELAY_MIN = 3.0
  PARSE_DELAY_MAX = 7.0
  ```

### npm не найден

Установите Node.js с https://nodejs.org/ и перезапустите терминал.

### Публикация на GitHub

Минимальный набор файлов для работы сервиса задаётся `.gitignore` (исключаются `tests/`, `scripts/`, `notebooks/`, `logs/`, `artifacts/`, `venv/` и т.д.). Для установки только runtime-зависимостей используйте `requirements-runtime.txt`. Пошаговая инструкция: [docs/deployment/GITHUB_PUBLISH.md](docs/deployment/GITHUB_PUBLISH.md).

**Репозиторий:** [github.com/dmitriygeo/candidate-scoring](https://github.com/dmitriygeo/candidate-scoring).

---

## Следующие шаги (Чекпоинт 3)

1. Модель для оценки релевантности кандидата (обучение на исторических данных)
2. Интеграция с GitHub для оценки активности
3. Парсинг рейтингов вузов (ВШЭ мониторинг)
4. Улучшение извлечения навыков с помощью NER


