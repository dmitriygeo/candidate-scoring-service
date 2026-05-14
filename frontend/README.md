# Candidate Scoring Frontend

Веб-интерфейс для системы скоринга кандидатов.

## 🚀 Быстрый старт

### Требования

- **Node.js** 18+ ([скачать](https://nodejs.org/))
- **Backend** должен быть запущен на `http://localhost:8000`

### Установка

```bash
# Перейти в папку frontend
cd frontend

# Установить зависимости
npm install

# Запустить dev сервер
npm run dev
```

Откройте http://localhost:3000

---

## 📋 Структура проекта

```
frontend/
├── public/                    # Статические файлы
├── src/
│   ├── api/
│   │   └── client.js         # API клиент (axios)
│   ├── components/
│   │   ├── ui/               # Базовые UI компоненты
│   │   │   ├── Badge.jsx
│   │   │   ├── Button.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── ProgressBar.jsx
│   │   │   └── Spinner.jsx
│   │   ├── layout/
│   │   │   └── Layout.jsx    # Общий layout с sidebar
│   │   ├── CandidateCard.jsx
│   │   ├── VacancyCard.jsx
│   │   └── MatchResultCard.jsx
│   ├── pages/
│   │   ├── Dashboard.jsx     # Главная страница
│   │   ├── Vacancies.jsx     # Список вакансий
│   │   ├── VacancyDetail.jsx # Детали вакансии
│   │   ├── Candidates.jsx    # Список кандидатов
│   │   ├── CandidateDetail.jsx
│   │   ├── Matching.jsx      # Матчинг кандидатов
│   │   ├── Parser.jsx        # Парсер HH.ru
│   │   └── Skills.jsx        # Анализ навыков
│   ├── App.jsx               # Главный компонент + роутинг
│   ├── main.jsx              # Точка входа
│   └── index.css             # Глобальные стили + Tailwind
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

---

## 🔧 Конфигурация

### Изменить URL API

Отредактируйте файл `.env`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

Или для production:

```env
VITE_API_URL=https://your-backend.com/api/v1
```

---

## 📱 Страницы

| Страница | URL | Описание |
|----------|-----|----------|
| Dashboard | `/` | Статистика и быстрые действия |
| Вакансии | `/vacancies` | Список всех вакансий |
| Детали вакансии | `/vacancies/:id` | Полная информация о вакансии |
| Кандидаты | `/candidates` | Список всех кандидатов |
| Детали кандидата | `/candidates/:id` | Полная информация о кандидате |
| Матчинг | `/matching/:vacancyId` | Поиск кандидатов для вакансии |
| Парсер | `/parser` | Загрузка данных с HH.ru |
| Навыки | `/skills` | Нормализация и извлечение навыков |

---

## 🛠 Технологии

- **React 18** - UI библиотека
- **Vite** - сборщик
- **React Router** - роутинг
- **TanStack Query** - кэширование и загрузка данных
- **Axios** - HTTP клиент
- **Tailwind CSS** - стилизация

---

## 📦 Сборка для production

```bash
npm run build
```

Готовые файлы будут в папке `dist/`.

### Деплой на Vercel

```bash
npm install -g vercel
vercel --prod
```

### Деплой на Netlify

1. Подключите репозиторий к Netlify
2. Build command: `npm run build`
3. Publish directory: `dist`

---

## 🔍 Решение проблем

### CORS ошибки

Убедитесь, что backend разрешает запросы с `http://localhost:3000`:

```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API недоступен

1. Проверьте, что backend запущен: http://localhost:8000/docs
2. Проверьте URL в `.env`
3. Проверьте консоль браузера на ошибки

### Стили не применяются

```bash
# Пересоберите Tailwind
npm run dev
```





