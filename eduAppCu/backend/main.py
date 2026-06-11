"""FastAPI application for EduApp backend"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.db import init_db

# Import routers
from routers import auth, subjects, user, plan, tasks, chat, tests, premium

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    init_db()
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="EduApp API",
    description="Backend for EduApp - a learning platform for exam preparation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(user.router)
app.include_router(plan.router)
app.include_router(tasks.router)
app.include_router(chat.router)
app.include_router(tests.router)
app.include_router(premium.router)


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5001,
        reload=True
    )
