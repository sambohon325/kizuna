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
    storage_backend: str = "local"
    storage_directory: str = "storage"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = ""
    s3_prefix: str = "kizuna"
    s3_presign_seconds: int = 900
    backup_retention_days: int = 30
    backup_max_copies: int = 10
    backup_scheduler_interval_seconds: int = 60
    worker_enrollment_secret: str = "local-dev-enrollment"
    worker_lease_seconds: int = 300
    max_artifact_bytes: int = 67_108_864
    ffmpeg_path: str = ""
    openai_api_key: str = ""
    voice_provider: str = "simulation"
    openai_voice_model: str = "gpt-4o-mini-tts"
    openai_voice: str = "coral"
    writer_provider: str = "simulation"
    openai_writer_model: str = "gpt-5.6-terra"
    director_provider: str = "simulation"
    openai_director_model: str = "gpt-5.6-terra"
    visual_agent_provider: str = "simulation"
    openai_visual_agent_model: str = "gpt-5.6-terra"
    animator_provider: str = "simulation"
    openai_animator_model: str = "gpt-5.6-terra"
    editor_provider: str = "simulation"
    openai_editor_model: str = "gpt-5.6-terra"


settings = Settings()
