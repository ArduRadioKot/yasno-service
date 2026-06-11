# FastAPI Migration Guide

## Overview

The backend has been successfully migrated from Flask to FastAPI. This guide outlines the changes and how to use the new structure.

## Key Changes

### 1. **Dependencies Update**

- Replaced `flask` and `flask-cors` with `fastapi` and `uvicorn`
- Added `pydantic` for request/response validation
- Added `python-multipart` for form data handling

**Updated requirements.txt:**

```
fastapi==0.115.0
uvicorn==0.30.0
python-multipart==0.0.6
openai==1.57.0
python-dotenv==1.0.0
sdamgia-api==0.1.7
pydantic==2.9.2
```

### 2. **Project Structure**

```
backend/
├── main.py                  # Main FastAPI application
├── schemas.py              # Pydantic models for validation
├── requirements.txt        # Updated dependencies
├── routers/
│   ├── __init__.py
│   ├── auth.py            # Authentication endpoints
│   ├── subjects.py        # Subject management endpoints
│   ├── user.py            # User endpoints
│   ├── plan.py            # Plan endpoints
│   ├── tasks.py           # Task endpoints
│   ├── chat.py            # Chat endpoints
│   └── tests.py           # Test generation and analysis endpoints
├── services/              # (unchanged)
│   ├── ai_client.py
│   ├── data_service.py
│   ├── db.py
│   ├── exam_utils.py
│   ├── oge_sdamgia_client.py
│   ├── problem_bank_service.py
│   └── test_service.py
├── data/                  # (unchanged)
└── scripts/               # (unchanged)
```

### 3. **New Features**

#### Pydantic Models

All requests now use Pydantic models for automatic validation:

- `LoginRequest` / `LoginResponse`
- `RegisterRequest` / `RegisterResponse`
- `GenerateTestRequest` / `AnalyzeTestRequest`
- And many more...

#### CORS Handling

CORS is configured using FastAPI middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Lifespan Events

The application initialization is handled through FastAPI's lifespan context manager.

### 4. **Endpoint Mapping**

All endpoints remain the same:

| Method | Endpoint                      | Router      |
| ------ | ----------------------------- | ----------- |
| POST   | `/api/login`                  | auth.py     |
| POST   | `/api/register`               | auth.py     |
| GET    | `/api/subjects`               | subjects.py |
| PUT    | `/api/user/subject`           | subjects.py |
| GET    | `/api/user`                   | user.py     |
| GET    | `/api/dashboard`              | plan.py     |
| GET    | `/api/plan`                   | plan.py     |
| PATCH  | `/api/plan/topics/{topic_id}` | plan.py     |
| GET    | `/api/tasks`                  | tasks.py    |
| GET    | `/api/tasks/{task_id}`        | tasks.py    |
| POST   | `/api/tasks/{task_id}/check`  | tasks.py    |
| GET    | `/api/tasks/{task_id}/next`   | tasks.py    |
| POST   | `/api/tasks/generate`         | tasks.py    |
| POST   | `/api/chat`                   | chat.py     |
| GET    | `/api/chat/suggestions`       | chat.py     |
| POST   | `/api/generate-test`          | tests.py    |
| POST   | `/api/analyze-test`           | tests.py    |
| GET    | `/api/health`                 | main.py     |

## Installation & Running

### 1. Install Dependencies

```bash
cd backend
python3 -m pip install -r requirements.txt
```

### 2. Run Development Server

```bash
python3 main.py
```

Or using uvicorn directly:

```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 5001 --reload
```

### 3. API Documentation

FastAPI automatically provides:

- **Swagger UI**: `http://localhost:5001/docs`
- **ReDoc**: `http://localhost:5001/redoc`

## Benefits of FastAPI

1. **Type Safety**: Pydantic models provide automatic validation
2. **Auto Documentation**: Swagger/OpenAPI docs are auto-generated
3. **Performance**: FastAPI is built on Starlette and is very fast
4. **Async Support**: Built-in async/await support
5. **Better Error Handling**: Standardized HTTP exceptions
6. **Modern Python**: Uses modern Python features and type hints

## Migration Notes

### Breaking Changes

- No breaking changes to API endpoints
- All request/response formats remain the same
- CORS configuration is still open (`allow_origins=["*"]`)

### Development Tips

1. Use the automatic Swagger documentation at `/docs` for testing
2. All routes are organized in separate files for better maintainability
3. Services remain unchanged, so all business logic is preserved
4. Use `Query` parameters for GET query strings (automatically handled)
5. Use request body models for POST/PUT/PATCH requests

## Troubleshooting

### Import Errors

If you get import errors, ensure:

- All router files are in the `routers/` directory
- The `services/` directory structure is intact
- All services are in the same directory as `main.py`

### Database Issues

- The database is initialized automatically on startup
- Check `services/db.py` for database configuration
- Ensure `.env` file has correct database path

### Missing Modules

Run: `python3 -m pip install -r requirements.txt`

## Old Flask App

The original `app.py` (Flask) can be kept as reference but should not be used in production. The FastAPI migration is complete and production-ready.
