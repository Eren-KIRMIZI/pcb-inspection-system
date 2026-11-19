"""I3 (ortak hata şeması) ve I8 (yapılandırılmış loglama) doğrulamaları."""

import json
import logging
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.logging_config import JsonFormatter
from backend.app.main import app

client = TestClient(app)


def _image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (400, 300), (20, 100, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _assert_common_schema(body: dict, expected_code: str) -> None:
    assert set(body) >= {"error", "detail", "request_id"}
    assert body["error"] == expected_code
    assert isinstance(body["detail"], str) and body["detail"]
    assert isinstance(body["request_id"], str) and body["request_id"]


def test_bad_image_returns_common_error_schema() -> None:
    response = client.post(
        "/api/v1/uploads",
        files={"file": ("not-an-image.jpg", b"not an image", "image/jpeg")},
    )
    assert response.status_code == 400
    _assert_common_schema(response.json(), "bad_request")
    assert response.headers.get("x-request-id")


def test_missing_reference_returns_not_found_schema() -> None:
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("board.jpg", _image_bytes(), "image/jpeg")},
        data={"reference_name": "olmayan-referans"},
    )
    assert response.status_code == 404
    body = response.json()
    _assert_common_schema(body, "not_found")
    assert "olmayan-referans" in body["detail"]


def test_validation_error_returns_common_schema() -> None:
    response = client.post("/api/v1/uploads")
    assert response.status_code == 422
    _assert_common_schema(response.json(), "validation_error")


def test_request_id_is_echoed() -> None:
    response = client.get(
        "/api/v1/history/count", headers={"X-Request-ID": "test-request-123"}
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-123"


class _CaptureHandler(logging.Handler):
    """Log satırlarını, istek bağlamı aktifken emit anında JSON olarak yakalar."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def test_inspection_emits_structured_log() -> None:
    handler = _CaptureHandler()
    handler.setFormatter(JsonFormatter())
    inspection_logger = logging.getLogger("backend.app.services.inspection")
    inspection_logger.addHandler(handler)
    try:
        response = client.post(
            "/api/v1/inspections",
            files={"file": ("logged-board.jpg", _image_bytes(), "image/jpeg")},
        )
    finally:
        inspection_logger.removeHandler(handler)

    assert response.status_code == 200
    payloads = [
        json.loads(line)
        for line in handler.lines
        if json.loads(line).get("event") == "inspection_completed"
    ]
    assert payloads, "inspection_completed log kaydı bulunamadı"
    payload = payloads[-1]
    assert payload["image_id"] == response.json()["image_id"]
    assert payload["engine"] in {"real", "mock"}
    assert payload["verdict"] in {"PASS", "FAIL", "MANUAL_REVIEW"}
    assert isinstance(payload["defect_count"], int)
    assert isinstance(payload["duration_ms"], int)
    assert isinstance(payload["decision_codes"], list)
    assert payload["request_id"] == response.headers["x-request-id"]


def test_json_formatter_fields() -> None:
    record = logging.LogRecord(
        name="backend.app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="test mesajı",
        args=(),
        exc_info=None,
    )
    record.event = "unit_event"
    record.image_id = "abc-123"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "unit_event"
    assert payload["message"] == "test mesajı"
    assert payload["logger"] == "backend.app.test"
    assert payload["level"] == "INFO"
    assert payload["image_id"] == "abc-123"
    assert payload["ts"].endswith("Z")
