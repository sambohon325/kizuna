from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KIZUNA_", env_file=".env")

    app_name: str = "Kizuna Studio"
    environment: str = "development"
    public_url: str = "http://127.0.0.1:8000"
    marketing_url: str = ""
    auth_required: bool = False
    bootstrap_admin_key: str = ""
    session_days: int = 7
    invitation_days: int = 7
    account_token_hours: int = 1
    account_email_limit_per_hour: int = 5
    email_verification_required: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    smtp_from_email: str = ""
    smtp_from_name: str = "Kizuna Studio"
    trial_days: int = 7
    trial_signup_enabled: bool = False
    trial_export_seconds: int = 60
    trial_watermark: str = "KIZUNA TRIAL | kizuna.technology"
    trial_signup_limit_per_hour: int = 5
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_creator_price_id: str = ""
    cookie_secure: bool = False
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
    storage_warning_free_gb: float = 10.0
    storage_warning_free_percent: float = 10.0
    log_level: str = "INFO"
    service_heartbeat_seconds: int = 15
    service_stale_seconds: int = 60
    scanner_health_url: str = ""
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = ""
    s3_prefix: str = "kizuna"
    s3_presign_seconds: int = 900
    backup_retention_days: int = 30
    backup_max_copies: int = 10
    backup_scheduler_interval_seconds: int = 60
    cleanup_verification_hours: int = 24
    redis_url: str = ""
    job_stream_key: str = "kizuna:jobs"
    job_lease_seconds: int = 600
    job_poll_seconds: float = 2.0
    job_inline_fallback: bool = True
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
    verification_admin_key: str = ""


settings = Settings()
