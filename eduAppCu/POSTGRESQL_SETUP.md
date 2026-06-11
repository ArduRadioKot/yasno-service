# PostgreSQL Setup & Premium Keys System

## 📋 Требования

- PostgreSQL 12+ установлен и запущен
- Python 3.8+
- psycopg2-binary (включен в requirements.txt)

## 🛠 Установка PostgreSQL

### macOS (Homebrew)

```bash
brew install postgresql@15
brew services start postgresql@15
```

### Linux (Ubuntu/Debian)

```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Windows

Скачайте с [postgresql.org](https://www.postgresql.org/download/windows/)

## 📦 Создание БД

### 1. Подключитесь к PostgreSQL

```bash
psql -U postgres
```

### 2. Создайте пользователя и БД

```sql
-- Создать пользователя
CREATE USER edu_app_user WITH PASSWORD 'your_secure_password';

-- Создать БД
CREATE DATABASE edu_app OWNER edu_app_user;

-- Выдать права
GRANT ALL PRIVILEGES ON DATABASE edu_app TO edu_app_user;

-- Выйти
\q
```

## 🔧 Конфигурация приложения

### 1. Создайте `.env` файл в папке `backend/`

```env
# PostgreSQL Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=edu_app
DB_USER=edu_app_user
DB_PASSWORD=your_secure_password

# AI Service
MISTRAL_API_KEY=your_api_key
MISTRAL_MODEL=mistral-small-latest

# Application
DEBUG=true
```

### 2. Установите зависимости

```bash
cd backend
pip install -r requirements.txt
```

### 3. Инициализируйте БД

```python
from services.db import init_db
init_db()
```

Или через бэкенд при первом запуске:

```bash
npm run backend
```

## 🔑 Система Премиум Ключей

### Структура таблицы `premium_keys`

```sql
CREATE TABLE premium_keys (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,              -- Уникальный ключ
    duration_days INTEGER DEFAULT 30,      -- Длительность подписки
    is_active BOOLEAN DEFAULT TRUE,        -- Активен ли ключ
    is_used BOOLEAN DEFAULT FALSE,         -- Использован ли ключ
    user_id INTEGER,                       -- ID пользователя (если активирован)
    created_at TIMESTAMP DEFAULT NOW(),    -- Дата создания
    expires_at TIMESTAMP,                  -- Дата истечения
    used_at TIMESTAMP,                     -- Дата активации
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

### API Endpoints

#### 1. Проверить ключ

```bash
POST /api/premium/validate
{
    "key": "PREMIUM-ABCD1234"
}

# Ответ
{
    "valid": true,
    "message": "Ключ доступен для активации",
    "key_id": 123
}
```

#### 2. Активировать ключ

```bash
POST /api/premium/activate
{
    "key": "PREMIUM-ABCD1234",
    "email": "user@example.com"
}

# Ответ
{
    "valid": true,
    "message": "Ключ успешно активирован",
    "expires_at": "2025-07-11T10:30:00"
}
```

#### 3. Получить статус премиума

```bash
GET /api/premium/status?email=user@example.com

# Ответ
{
    "is_premium": true,
    "expires_at": "2025-07-11T10:30:00",
    "days_left": 30,
    "message": "Подписка активна"
}
```

#### 4. Проверить премиум статус

```bash
POST /api/premium/check
{
    "email": "user@example.com"
}

# Ответ
{
    "is_premium": true,
    "expires_at": "2025-07-11T10:30:00",
    "days_left": 30,
    "message": "Пользователь имеет активную подписку"
}
```

## 🤖 Telegram Bot команды

Поместите ID администратора в переменную `ADMIN_IDS` в `bot/bot.py`:

```python
ADMIN_IDS = [123456789]  # Ваш Telegram ID
```

### Команды администратора

#### `/generate` - Создать премиум ключ

```
Создаёт новый ключ на 30 дней в БД
```

#### `/keys` - Список ключей

```
Показывает последние 10 созданных ключей с статусом
```

#### `/help` - Справка

```
Показывает все доступные команды
```

### Команды пользователя

#### `/start` - Начало работы

```
Показывает кнопку оплаты подписки
```

#### `/pay` - Оплата подписки

```
Инициирует платёж через Telegram Stars (XTR)
```

### Процесс оплаты

1. Пользователь нажимает кнопку 💳 Оплатить подписку
2. Вводит платёж через Telegram Stars
3. Бот автоматически генерирует ключ
4. Ключ отправляется пользователю
5. Ключ сохраняется в БД с флагом `is_used=true`

## 🔍 Функции БД

### Python функции для работы с ключами

```python
from services.db import (
    create_premium_key,           # Создать новый ключ
    validate_premium_key,         # Проверить валидность ключа
    activate_premium_key,         # Активировать ключ для пользователя
    get_user_premium_status,      # Получить статус подписки
    revoke_premium_key,           # Отозвать ключ
    list_premium_keys             # Список всех ключей
)

# Примеры использования

# Создать ключ на 30 дней
key = create_premium_key(duration_days=30)
# Результат: "PREMIUM-ABC123XYZ456"

# Проверить ключ
result = validate_premium_key("PREMIUM-ABC123XYZ456")
# Результат: {"valid": True, "message": "...", ...}

# Активировать для пользователя
result = activate_premium_key("PREMIUM-ABC123XYZ456", user_id=5)
# Результат: {"valid": True, "message": "Ключ успешно активирован"}

# Получить статус подписки
status = get_user_premium_status(user_id=5)
# Результат: {"is_premium": True, "expires_at": "...", "days_left": 30}

# Получить список ключей
keys = list_premium_keys(limit=50)
# Результат: [{"id": 1, "key": "...", "is_active": True, ...}, ...]
```

## ✅ Проверка работы

### 1. Проверить подключение к БД

```bash
psql -U edu_app_user -d edu_app -c "\dt"
```

### 2. Проверить таблицы

```sql
SELECT * FROM premium_keys;
SELECT * FROM users;
SELECT * FROM user_settings;
```

### 3. Запустить бэкенд

```bash
npm run backend
```

### 4. Посетить документацию API

```
http://localhost:5001/docs
```

## 🐛 Troubleshooting

### PostgreSQL не запускается

```bash
# macOS
brew services restart postgresql@15

# Linux
sudo systemctl restart postgresql
```

### Ошибка подключения "connection refused"

- Проверьте, что PostgreSQL запущен
- Проверьте параметры в `.env`
- Убедитесь, что пользователь существует

### Таблицы не создаются

```python
# Запустите вручную
from services.db import init_db
init_db()
```

### Ошибки миграции с SQLite

- Старый SQLite файл: `backend/data/edu_app.db`
- БД автоматически инициализируется при первом запуске
- Данные SQLite не переносятся автоматически

## 📝 Примеры использования в коде

### Фронтенд (React/TypeScript)

```typescript
// Проверить статус премиума
const checkPremium = async (email: string) => {
  const response = await fetch("http://localhost:5001/api/premium/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  return await response.json();
};

// Активировать ключ
const activateKey = async (key: string, email: string) => {
  const response = await fetch("http://localhost:5001/api/premium/activate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, email }),
  });
  return await response.json();
};
```

### Бэкенд (FastAPI)

```python
from services.db import get_user_premium_status

# В эндпоинте
@app.get("/api/protected")
async def protected_endpoint(email: str):
    user = get_user_by_email(email)
    status = get_user_premium_status(user["id"])

    if not status["is_premium"]:
        raise HTTPException(status_code=403, detail="Требуется премиум подписка")

    return {"message": "Доступ разрешён"}
```

## 🚀 Production Deployment

1. Используйте сильные пароли для БД
2. Настройте SSL для PostgreSQL
3. Регулярно делайте резервные копии
4. Используйте переменные окружения для всех секретов
5. Включите логирование запросов к БД

---

Система полностью готова! 🎉
