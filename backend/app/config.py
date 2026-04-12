from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://user:password@localhost/propiq_db"
    SECRET_KEY: str = "REPLACE_WITH_STRONG_SECRET_IN_ENV_FILE"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    AI_SERVICE_URL: str = "http://localhost:8100"
    AI_SERVICE_TIMEOUT_SECONDS: float = 8.0

    model_config = {"env_file": ".env"}


settings = Settings()
