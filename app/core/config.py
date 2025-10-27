from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 🔐 Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str

    # Project
    PROJECT_NAME: str = "FastAPI With React"
    DEBUG: bool = True

    class Config:
        env_file = ".env"  # Load environment variables from .env
        env_file_encoding = "utf-8"

# Create a single settings instance
settings = Settings()
