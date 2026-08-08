from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KIZUNA_", env_file=".env")

    app_name: str = "Kizuna Studio"
    environment: str = "development"
    database_url: str = "sqlite:///./anime_studio.db"


settings = Settings()

