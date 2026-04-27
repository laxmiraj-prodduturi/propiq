from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Property Manager AI Service"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    DEMO_MODE: bool = True
    CHROMA_DB_PATH: str = str(Path(__file__).parent.parent / "chroma_db")

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
