"""Configuration settings for Jarvis backend."""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    DEEPGRAM_API_KEY: str
    OPENAI_API_KEY: str
    ELEVENLABS_API_KEY: str
    PINECONE_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    COMPANY_API_KEY: Optional[str] = None

    # Tool Configuration
    PINECONE_INDEX_NAME: str = "jarvis-docs"
    COMPANY_API_URL: str = "http://localhost:8000"

    # Backend Configuration
    BACKEND_PORT: int = 8000
    BACKEND_HOST: str = "0.0.0.0"

    # Server Configuration (for FastAPI)
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database Configuration
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCOUNT_ID: Optional[str] = None

    # Development Flags
    NODE_ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
