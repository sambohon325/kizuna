from pydantic_settings import BaseSettings, SettingsConfigDict


class ScannerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KIZUNA_SCANNER_", env_file=".env", extra="ignore")

    corpus_directory: str = "scanner-corpus"
    render_directory: str = "renders"
    storage_directory: str = "storage"
    api_key: str = ""
    admin_key: str = ""
    ffmpeg_path: str = ""
    max_input_bytes: int = 8_388_608
    text_threshold: float = 0.38
    title_threshold: float = 0.88
    visual_threshold: float = 0.90
    audio_threshold: float = 0.92


settings = ScannerSettings()
