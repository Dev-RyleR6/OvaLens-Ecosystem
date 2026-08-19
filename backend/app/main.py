import os
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.exceptions import OvaLensAPIException, ovalens_exception_handler
from app.api.v1.router import api_router

# Ensure all ORM models are registered with Base
import app.models  # noqa: F401

# Auto-create tables on startup
Base.metadata.create_all(bind=engine)

# Ensure local storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Industrial-Grade Central Backend API for the OvaLens Automated Duck Egg Candling & Hatchery Ecosystem.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(OvaLensAPIException, ovalens_exception_handler)

# Mount Candling Photo Storage
app.mount("/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "online",
        "docs_url": "/docs"
    }


@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "version": settings.VERSION
    }
