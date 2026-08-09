from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KIZUNA_", env_file=".env")

    app_name: str = "Kizuna Studio"
    environment: str = "development"
    database_url: str = "sqlite:///./anime_studio.db"
    generation_provider: str = "mock"
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_workflow_path: str = ""
    comfyui_positive_node: str = "6"
    comfyui_negative_node: str = "7"
    comfyui_sampler_node: str = "3"
    render_directory: str = "renders"
    worker_enrollment_secret: str = "local-dev-enrollment"
    worker_lease_seconds: int = 300
    max_artifact_bytes: int = 67_108_864


settings = Settings()
