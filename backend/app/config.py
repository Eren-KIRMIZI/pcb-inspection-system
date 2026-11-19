from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Uygulama ayarları. Ortam değişkenleri veya .env dosyası ile geçersiz kılınabilir."""

    app_name: str = "PCB Inspection API"
    api_prefix: str = "/api/v1"
    upload_dir: Path = Path("data/uploads")
    results_dir: Path = Path("data/results")
    max_upload_mb: int = 20
    model_path: Path | None = None
    device: str = "cpu"
    conf_threshold: float = 0.25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
