# Backend - FastAPI

## Запуск

### Способ 1: Через npm (рекомендуется)

```bash
npm run backend
```

Этот скрипт:

- Создаст виртуальное окружение (если его нет)
- Установит все зависимости
- Запустит FastAPI сервер на `http://localhost:5001`

### Способ 2: Прямой запуск Python

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # На Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 5001 --reload
```

### Способ 3: Через скрипт setup

```bash
cd backend
bash setup.sh
npm run backend
```

## API Документация

После запуска сервера откройте в браузере:

- **Swagger UI**: http://localhost:5001/docs
- **ReDoc**: http://localhost:5001/redoc

Там вы увидите все 18+ эндпоинтов с полной документацией.

## Структура проекта

```
backend/
├── main.py                    # FastAPI приложение
├── schemas.py                 # Pydantic модели
├── requirements.txt           # Зависимости
├── setup.sh                   # Скрипт установки
├── routers/                   # Маршруты (разделены по функциям)
│   ├── auth.py               # Аутентификация
│   ├── subjects.py           # Предметы
│   ├── user.py               # Пользователь
│   ├── plan.py               # План обучения
│   ├── tasks.py              # Задачи
│   ├── chat.py               # AI чат
│   └── tests.py              # Тесты
├── services/                 # Бизнес-логика
└── data/                     # Данные
```

## Переменные окружения

Создайте файл `.env` в папке `backend/`:

```env
# Обязательные переменные (если используется AI)
MISTRAL_API_KEY=your_key_here
MISTRAL_MODEL=mistral-large

# Опциональные
DEBUG=true
```

## Основные эндпоинты

| Метод | Путь                  | Описание             |
| ----- | --------------------- | -------------------- |
| GET   | `/api/health`         | Проверка статуса     |
| POST  | `/api/login`          | Вход пользователя    |
| POST  | `/api/register`       | Регистрация          |
| GET   | `/api/subjects`       | Список предметов     |
| GET   | `/api/plan`           | План обучения        |
| GET   | `/api/tasks`          | Список задач         |
| POST  | `/api/tasks/generate` | Генерирование задачи |
| POST  | `/api/chat`           | AI чат               |
| POST  | `/api/generate-test`  | Создание теста       |
| POST  | `/api/analyze-test`   | Анализ результатов   |

Полный список эндпоинтов доступен в `/docs`.

## Отладка

### Все зависимости установлены?

```bash
pip list
```

### Конфликты портов?

Если порт 5001 занят, измените его в команде:

```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Проблемы с импортами?

```bash
# Проверьте, находитесь в папке backend
cd backend
# Попробуйте импортировать модули напрямую
python3 -c "import main; print('OK')"
```

## Разработка

### Автоперезагрузка

Флаг `--reload` включен, поэтому при изменении файлов сервер автоматически перезагружается.

### Добавление нового эндпоинта

1. Создайте новый маршрут в `routers/new_router.py`
2. Импортируйте его в `main.py`
3. Добавьте через `app.include_router()`

Пример:

```python
# routers/new_router.py
from fastapi import APIRouter
from schemas import SomeModel

router = APIRouter(prefix="/api", tags=["new"])

@router.get("/new-endpoint")
async def new_endpoint():
    return {"message": "Hello"}
```

```python
# main.py
from routers import new_router
app.include_router(new_router.router)
```

## Проблемы?

- Проверьте Python версию: `python3 --version` (требуется 3.8+)
- Убедитесь, что `main.py` находится в папке `backend`
- Проверьте, что `requirements.txt` имеет все необходимые пакеты

Для подробной информации о миграции см. `FASTAPI_MIGRATION.md` и `MIGRATION_SUMMARY.md`.
