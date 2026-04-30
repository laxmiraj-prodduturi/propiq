from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required — no defaults so startup fails explicitly if .env is absent
    DATABASE_URL: str
    SECRET_KEY: str

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    AI_SERVICE_URL: str = "http://localhost:8100"
    AI_SERVICE_TIMEOUT_SECONDS: float = 60.0
    # Set to true in production (requires HTTPS); false only for local HTTP dev
    COOKIE_SECURE: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
