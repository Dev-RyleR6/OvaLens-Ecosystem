import os
from typing import List
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load .env file from backend root
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

try:
    # pyrefly: ignore [missing-import]
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _HAVE_PYDANTIC_SETTINGS = True
except ImportError:
    _HAVE_PYDANTIC_SETTINGS = False


if _HAVE_PYDANTIC_SETTINGS:
    class Settings(BaseSettings):
        PROJECT_NAME: str = "OvaLens Hatchery API"
        VERSION: str = "2.0.0"
        API_V1_STR: str = "/api/v1"
        ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

        DB_USER: str = os.getenv("DB_USER", "postgres")
        DB_PASS: str = os.getenv("DB_PASS", "postgres123")
        DB_HOST: str = os.getenv("DB_HOST", "localhost")
        DB_PORT: str = os.getenv("DB_PORT", "5432")
        DB_NAME: str = os.getenv("DB_NAME", "hatchery_db")

        API_KEY: str = os.getenv("API_KEY", "dev-api-key-123")
        JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-ovalens-capstone-2026")
        JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

        CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
        STORAGE_DIR: str = os.getenv("STORAGE_DIR", "storage/candling_scans")

        @property
        def database_url(self) -> str:
            return f"postgresql://{self.DB_USER}:{quote_plus(self.DB_PASS)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

        @property
        def cors_origins_list(self) -> List[str]:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

        model_config = SettingsConfigDict(env_file=env_path, env_file_encoding="utf-8", extra="ignore")

    settings = Settings()

else:
    class Settings:
        PROJECT_NAME: str = "OvaLens Hatchery API"
        VERSION: str = "2.0.0"
        API_V1_STR: str = "/api/v1"
        ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

        DB_USER: str = os.getenv("DB_USER", "postgres")
        DB_PASS: str = os.getenv("DB_PASS", "postgres123")
        DB_HOST: str = os.getenv("DB_HOST", "localhost")
        DB_PORT: str = os.getenv("DB_PORT", "5432")
        DB_NAME: str = os.getenv("DB_NAME", "hatchery_db")

        API_KEY: str = os.getenv("API_KEY", "dev-api-key-123")
        JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-ovalens-capstone-2026")
        JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

        CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
        STORAGE_DIR: str = os.getenv("STORAGE_DIR", "storage/candling_scans")

        @property
        def database_url(self) -> str:
            return f"postgresql://{self.DB_USER}:{quote_plus(self.DB_PASS)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

        @property
        def cors_origins_list(self) -> List[str]:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    settings = Settings()
