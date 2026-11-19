"""D8: komponent modeli hatası kusur modeliyle aynı 503 sınıfını kullanır."""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.config import settings
from backend.app.errors import ModelUnavailableError
from backend.app.main import app
from backend.app.services import components, inspection

client = TestClient(app)


def _image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (400, 300), (20, 100, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_missing_component_model_raises_model_unavailable(tmp_path: Path) -> None:
    with pytest.raises(ModelUnavailableError) as excinfo:
        components.ComponentDetector(tmp_path / "missing.pt", 0.2, 640, "cpu")

    assert excinfo.value.status_code == 503
    assert "Komponent model dosyası bulunamadı" in excinfo.value.detail


def test_get_component_detector_propagates_model_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "component_model_path", tmp_path / "missing.pt")
    monkeypatch.setattr(components, "_detector", None)

    with pytest.raises(ModelUnavailableError):
        components.get_component_detector()


def test_inspection_with_missing_component_model_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable() -> components.ComponentDetector:
        raise ModelUnavailableError("Komponent model dosyası bulunamadı")

    monkeypatch.setattr(inspection, "get_component_detector", _unavailable)

    response = client.post(
        "/api/v1/inspections",
        files={"file": ("board.jpg", _image_bytes(), "image/jpeg")},
        data={"reference_name": "demo"},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "model_unavailable"
    assert "Komponent model" in body["detail"]
