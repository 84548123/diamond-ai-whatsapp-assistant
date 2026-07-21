from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "AI WhatsApp Assistant"
    SECRET_KEY: str = "super-secret-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/aiwa"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBED_MODEL: str = "text-embedding-004"

    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "verify-token-123"
    WHATSAPP_WEBHOOK_URL: str = ""

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    RATE_LIMIT_PER_MINUTE: int = 60

    # Stock CSV
    STOCK_CSV_PATH: str = "data/stock_list.csv"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()

# Ensure directories
os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
