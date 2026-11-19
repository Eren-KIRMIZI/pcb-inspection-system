from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.schemas import (
    Decision,
    DefectCount,
    Detection,
    InspectionResult,
    ModelInfo,
)
from backend.app.services.history import overview, save_result

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


def _insert_result(day: str, verdict: str, defects: list[str]) -> None:
    """İzole test DB'sine belirli bir güne ait gerçek şemalı kayıt ekler."""

    detections = [
        Detection(
            class_id=index,
            class_name=name,
            confidence=0.9,
            bbox=[0.0, 0.0, 10.0, 10.0],
        )
        for index, name in enumerate(defects)
    ]
    save_result(
        InspectionResult(
            image_id=uuid4(),
            original_image_path="data/uploads/period-test.jpg",
            filename=f"period-test-{day}.jpg",
            verdict=verdict,  # type: ignore[arg-type]
            decision=Decision(verdict=verdict, reasons=[]),  # type: ignore[arg-type]
            engine="real",
            model=ModelInfo(defect_model="test", device="cpu", engine="real"),
            defects=detections,
            counts={name: defects.count(name) for name in set(defects)},
            image_width=640,
            image_height=480,
            duration_ms=1,
            created_at=datetime.fromisoformat(f"{day}T12:00:00+00:00"),
        )
    )


def test_overview_filters_all_kpis_by_custom_date_range() -> None:
    _insert_result("2020-03-02", "PASS", [])
    _insert_result("2020-03-03", "FAIL", ["excess_solder", "excess_solder", "solder_bridge"])
    _insert_result("2021-07-15", "PASS", [])

    stats = client.get(
        "/api/v1/history/overview",
        params={"date_from": "2020-03-02", "date_to": "2020-03-03"},
    ).json()

    assert stats["period"] == {"start": "2020-03-02", "end": "2020-03-03", "days": 2}
    assert stats["total_inspections"] == 2
    assert stats["pass_count"] == 1
    assert stats["fail_count"] == 1
    assert stats["defect_count"] == 3
    assert stats["pass_rate"] == 50.0
    assert stats["all_time_count"] >= stats["total_inspections"]
    assert len(stats["trend"]) == 2
    assert {point["date"] for point in stats["trend"]} == {"2020-03-02", "2020-03-03"}
    assert {entry["class_name"]: entry["count"] for entry in stats["defect_distribution"]} == {
        "excess_solder": 2,
        "solder_bridge": 1,
    }
    assert all(entry["filename"] != "period-test-2021-07-15.jpg" for entry in stats["recent"])
    assert stats["all_time_count"] > stats["total_inspections"]


def test_overview_compares_with_previous_period() -> None:
    _insert_result("2020-01-26", "PASS", ["excess_solder", "excess_solder"])
    _insert_result("2020-01-30", "FAIL", ["solder_bridge", "burn"])
    _insert_result("2020-02-03", "FAIL", ["excess_solder"])

    stats = overview(date_from="2020-02-01", date_to="2020-02-07")

    assert stats.total_inspections == 1
    assert stats.defect_count == 1
    assert stats.previous is not None
    assert stats.previous.total_inspections == 2
    assert stats.previous.total_delta == -1
    assert stats.previous.total_change_pct == -50.0
    assert stats.previous.defect_count == 4
    assert stats.previous.defect_delta == -3
    assert stats.previous.defect_change_pct == -75.0


def test_overview_rejects_invalid_date_range() -> None:
    invalid_month = client.get(
        "/api/v1/history/overview",
        params={"date_from": "2020-13-01", "date_to": "2020-13-05"},
    )
    assert invalid_month.status_code == 400
    body = invalid_month.json()
    assert set(body) >= {"error", "detail", "request_id"}
    assert invalid_month.headers.get("x-request-id")

    reversed_range = client.get(
        "/api/v1/history/overview",
        params={"date_from": "2020-03-10", "date_to": "2020-03-01"},
    )
    assert reversed_range.status_code == 400
    assert "date_from" in reversed_range.json()["detail"]


def test_status_endpoint_reports_actual_resources() -> None:
    response = client.get("/api/v1/status")
    assert response.status_code == 200, response.text
    body = response.json()

    assert set(body) == {"api", "defect_model", "component_model", "storage", "database"}
    for resource in body.values():
        assert resource["status"] in {"ok", "warning", "error"}
        assert resource["detail"]

    assert body["api"]["status"] == "ok"
    assert body["database"]["status"] == "ok"
    assert body["storage"]["status"] in {"ok", "error"}
    assert body["defect_model"]["status"] != "warning" or "Mock" in body["defect_model"]["detail"]
