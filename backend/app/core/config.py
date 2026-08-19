import os
from typing import List, Union
from urllib.parse import quote_plus
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central Application Settings & Environment Configuration (12-Factor Compliant).
    Automatically loads from OS environment variables and .env file with strong type casting.
    """
    PROJECT_NAME: str = "OvaLens Hatchery API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # PostgreSQL Relational Database Configuration
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres123"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "hatchery_db"

    # Security, JWT & API Key Authentication
    API_KEY: str = "dev-api-key-123"
    JWT_SECRET: str = "super-secret-jwt-key-ovalens-capstone-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Cross-Origin Resource Sharing (CORS) & Storage
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    STORAGE_DIR: str = "storage/candling_scans"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def database_url(self) -> str:
        """Construct a URL-encoded PostgreSQL connection string."""
        encoded_pass = quote_plus(str(self.DB_PASS))
        return f"postgresql://{self.DB_USER}:{encoded_pass}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins strictly as a list of strings."""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in str(self.CORS_ORIGINS).split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


# Instantiate singleton settings instance
settings = Settings()
