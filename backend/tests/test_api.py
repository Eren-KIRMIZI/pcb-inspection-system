from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app

client = TestClient(app)


def _sample_image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (400, 300), (0, 160, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_inspection_flow_returns_complete_result() -> None:
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("board.jpg", _sample_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["engine"] in {"real", "mock"}
    assert body["verdict"] == body["decision"]["verdict"]
    assert body["decision"]["reasons"]
    assert body["model"]["engine"] == body["engine"]
    assert isinstance(body["defects"], list)
    assert body["image_width"] == 400
    assert body["image_height"] == 300
    assert body["duration_ms"] >= 0
    assert body["annotated_image_path"]
    assert body["report_json_path"]
    assert body["report_pdf_path"]

    media_path = "/" + body["annotated_image_path"].replace("data/", "media/")
    assert client.get(media_path).status_code == 200


def test_tiny_image_is_rejected() -> None:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), (0, 160, 0)).save(buffer, format="JPEG")
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("tiny.jpg", buffer.getvalue(), "image/jpeg")},
    )
    assert response.status_code == 400
    assert "çok küçük" in response.json()["detail"]


def test_invalid_file_type_is_rejected() -> None:
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


def test_unknown_reference_returns_404() -> None:
    response = client.post(
        "/api/v1/inspections",
        data={"reference_name": "does_not_exist"},
        files={"file": ("board.jpg", _sample_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 404
