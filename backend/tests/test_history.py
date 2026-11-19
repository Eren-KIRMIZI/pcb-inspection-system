from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app

client = TestClient(app)


def _sample_image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (400, 300), (10, 120, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _create_inspection() -> dict:
    response = client.post(
        "/api/v1/inspections",
        files={"file": ("history-board.jpg", _sample_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_inspection_is_persisted_in_history() -> None:
    created = _create_inspection()
    entries = client.get("/api/v1/history", params={"limit": 5}).json()
    assert any(entry["image_id"] == created["image_id"] for entry in entries)

    first = entries[0]
    assert first["verdict"] in {"PASS", "FAIL", "MANUAL_REVIEW"}
    assert first["defect_count"] == len(created["defects"])
    assert "created_at" in first


def test_history_detail_returns_full_result() -> None:
    created = _create_inspection()
    response = client.get(f"/api/v1/history/{created['image_id']}")
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["decision"]["reasons"]
    assert detail["engine"] == created["engine"]
    assert detail["model"]["defect_model"]


def test_history_filter_and_count() -> None:
    created = _create_inspection()
    entries = client.get(
        "/api/v1/history",
        params={"verdict": created["verdict"], "search": "history-board"},
    ).json()
    assert entries
    assert all(entry["verdict"] == created["verdict"] for entry in entries)

    count = client.get(
        "/api/v1/history/count",
        params={"verdict": created["verdict"], "search": "history-board"},
    ).json()
    assert count["total"] >= len(entries)


def test_overview_returns_real_data() -> None:
    _create_inspection()
    stats = client.get("/api/v1/history/overview", params={"days": 7}).json()
    assert stats["total_inspections"] >= 1
    assert len(stats["trend"]) == 7
    assert 0 <= stats["pass_rate"] <= 100
    assert stats["pass_count"] + stats["fail_count"] + stats["manual_review_count"] <= stats["total_inspections"]
    assert isinstance(stats["defect_distribution"], list)
    assert isinstance(stats["recent"], list)


def test_models_endpoint_marks_metrics_as_unmeasured_in_app() -> None:
    body = client.get("/api/v1/models").json()
    assert body["measured_in_app"] is False
    assert "Precision" in body["unmeasured_metrics"]
    assert any(model["id"] == "solder-defect" for model in body["models"])
    assert any(model["id"] == "component-detection" for model in body["models"])
    assert all("Model kartı" in model["source"] for model in body["models"])


def test_settings_endpoint_exposes_active_configuration() -> None:
    body = client.get("/api/v1/settings").json()
    assert body["engine"] in {"real", "mock"}
    assert body["device"] in {"cpu", "0"}
    assert body["min_image_width"] > 0
    assert body["max_upload_mb"] > 0
    assert 0 <= body["reference_component_min_confidence"] <= 1


def test_references_list_is_available() -> None:
    response = client.get("/api/v1/references")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_missing_history_record_returns_404() -> None:
    response = client.get("/api/v1/history/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
