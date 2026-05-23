from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = (
        "postgresql+asyncpg://fleet:fleet@localhost:5433/fleet_telemetry"
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
