from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app

client = TestClient(app)


def _sample_image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), (0, 160, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_inspection_flow_with_mock_detector() -> None:
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("board.jpg", _sample_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["verdict"] in {"PASS", "FAIL", "MANUAL_REVIEW"}
    assert isinstance(body["defects"], list)
    assert body["annotated_image_path"]
    assert body["report_json_path"]
    assert body["report_pdf_path"]

    media_path = "/" + body["annotated_image_path"].replace("data/", "media/")
    assert client.get(media_path).status_code == 200
