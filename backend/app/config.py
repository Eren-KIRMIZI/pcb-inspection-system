from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Uygulama ayarları. Ortam değişkenleri veya .env dosyası ile geçersiz kılınabilir."""

    app_name: str = "PCB Inspection API"
    api_prefix: str = "/api/v1"
    data_dir: Path = BASE_DIR / "data"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    results_dir: Path = BASE_DIR / "data" / "results"
    max_upload_mb: int = 20
    model_path: Path | None = None
    device: str = "cpu"
    conf_threshold: float = 0.25
    use_mock_detector: bool = True
    manual_review_min_confidence: float = 0.40
    fail_min_confidence: float = 0.65

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
