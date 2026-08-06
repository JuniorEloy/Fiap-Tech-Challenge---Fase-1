from pydantic_settings import BaseSettings, SettingsConfigDict
import os

APP_ENV = os.getenv("APP_ENV", "prod")


class Settings(BaseSettings):
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    POSTGRES_DB: str
    IS_PRODUCTION: bool
    SECRET_KEY: str
    ALGORITHM: str
    JWT_ISSUER: str
    JWT_AUDIENCE: str

    model_config = SettingsConfigDict(
        env_file=f".env.{APP_ENV}",
        extra="ignore",
    )


settings = Settings()
