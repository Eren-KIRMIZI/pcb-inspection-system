import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID

from ..config import settings
from ..schemas import (
    DefectCount,
    HistoryEntry,
    InspectionResult,
    OverviewStats,
    TrendPoint,
)

_lock = Lock()


def _connect() -> sqlite3.Connection:
    db_path = settings.history_db_path or settings.data_dir / "inspections.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), timeout=15)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _lock, _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS inspections (
                image_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                filename TEXT NOT NULL,
                verdict TEXT NOT NULL,
                engine TEXT NOT NULL,
                defect_count INTEGER NOT NULL,
                top_defect TEXT,
                reference_name TEXT,
                reference_issues INTEGER NOT NULL DEFAULT 0,
                duration_ms INTEGER NOT NULL,
                image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL,
                annotated_image_path TEXT,
                report_json_path TEXT,
                report_pdf_path TEXT,
                result_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_inspections_created
                ON inspections(created_at DESC);
            CREATE TABLE IF NOT EXISTS inspection_defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id TEXT NOT NULL,
                class_name TEXT NOT NULL,
                confidence REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_defects_class
                ON inspection_defects(class_name);
            """
        )


def _entry(row: sqlite3.Row) -> HistoryEntry:
    return HistoryEntry(
        image_id=UUID(row["image_id"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        filename=row["filename"],
        verdict=row["verdict"],
        engine=row["engine"],
        defect_count=row["defect_count"],
        top_defect=row["top_defect"],
        reference_name=row["reference_name"],
        reference_issues=row["reference_issues"],
        duration_ms=row["duration_ms"],
        image_width=row["image_width"],
        image_height=row["image_height"],
        annotated_image_path=row["annotated_image_path"],
        report_json_path=row["report_json_path"],
        report_pdf_path=row["report_pdf_path"],
    )


def save_result(result: InspectionResult) -> None:
    top_defect = max(result.counts, key=result.counts.get) if result.counts else None
    reference_issues = (
        len(result.reference_check.issues) if result.reference_check else 0
    )
    with _lock, _connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO inspections (
                image_id, created_at, filename, verdict, engine, defect_count,
                top_defect, reference_name, reference_issues, duration_ms,
                image_width, image_height, annotated_image_path,
                report_json_path, report_pdf_path, result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(result.image_id),
                result.created_at.isoformat(),
                result.filename,
                result.verdict,
                result.engine,
                len(result.defects),
                top_defect,
                result.reference_check.reference if result.reference_check else None,
                reference_issues,
                result.duration_ms,
                result.image_width,
                result.image_height,
                result.annotated_image_path,
                result.report_json_path,
                result.report_pdf_path,
                result.model_dump_json(),
            ),
        )
        connection.execute(
            "DELETE FROM inspection_defects WHERE image_id = ?",
            (str(result.image_id),),
        )
        connection.executemany(
            "INSERT INTO inspection_defects (image_id, class_name, confidence) VALUES (?, ?, ?)",
            [
                (str(result.image_id), defect.class_name, defect.confidence)
                for defect in result.defects
            ],
        )


def list_results(
    limit: int = 50,
    offset: int = 0,
    verdict: str | None = None,
    engine: str | None = None,
    search: str | None = None,
) -> list[HistoryEntry]:
    clauses: list[str] = []
    params: list[object] = []
    if verdict:
        clauses.append("verdict = ?")
        params.append(verdict)
    if engine:
        clauses.append("engine = ?")
        params.append(engine)
    if search:
        clauses.append("(LOWER(filename) LIKE ? OR LOWER(image_id) LIKE ?)")
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM inspections {where} "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return [_entry(row) for row in rows]


def count_results(
    verdict: str | None = None,
    engine: str | None = None,
    search: str | None = None,
) -> int:
    clauses: list[str] = []
    params: list[object] = []
    if verdict:
        clauses.append("verdict = ?")
        params.append(verdict)
    if engine:
        clauses.append("engine = ?")
        params.append(engine)
    if search:
        clauses.append("(LOWER(filename) LIKE ? OR LOWER(image_id) LIKE ?)")
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _connect() as connection:
        return int(
            connection.execute(
                f"SELECT COUNT(*) FROM inspections {where}", params
            ).fetchone()[0]
        )


def get_result(image_id: str) -> dict | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT result_json FROM inspections WHERE image_id = ?", (image_id,)
        ).fetchone()
    return json.loads(row["result_json"]) if row else None


def overview(days: int = 7, recent_limit: int = 8) -> OverviewStats:
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=days - 1)

    with _connect() as connection:
        totals = dict(
            connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN verdict = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
                    SUM(CASE WHEN verdict = 'FAIL' THEN 1 ELSE 0 END) AS fail_count,
                    SUM(CASE WHEN verdict = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) AS review_count,
                    SUM(CASE WHEN reference_name IS NOT NULL THEN 1 ELSE 0 END) AS reference_checks
                FROM inspections
                """
            ).fetchone()
        )
        rows = connection.execute(
            """
            SELECT substr(created_at, 1, 10) AS day,
                   COUNT(*) AS total,
                   SUM(CASE WHEN verdict = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
                   SUM(CASE WHEN verdict = 'FAIL' THEN 1 ELSE 0 END) AS fail_count,
                   SUM(CASE WHEN verdict = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) AS review_count
            FROM inspections
            WHERE substr(created_at, 1, 10) >= ?
            GROUP BY day ORDER BY day
            """,
            (first_day.isoformat(),),
        ).fetchall()
        defects = connection.execute(
            """
            SELECT class_name, COUNT(*) AS count
            FROM inspection_defects
            GROUP BY class_name ORDER BY count DESC
            """
        ).fetchall()
        recent_rows = connection.execute(
            "SELECT * FROM inspections ORDER BY created_at DESC LIMIT ?",
            (recent_limit,),
        ).fetchall()

    trend_by_day = {row["day"]: row for row in rows}
    trend: list[TrendPoint] = []
    for index in range(days):
        day = (first_day + timedelta(days=index)).isoformat()
        row = trend_by_day.get(day)
        trend.append(
            TrendPoint(
                date=day,
                total=row["total"] if row else 0,
                pass_count=row["pass_count"] if row else 0,
                fail_count=row["fail_count"] if row else 0,
                manual_review_count=row["review_count"] if row else 0,
            )
        )

    total = totals.get("total") or 0
    return OverviewStats(
        total_inspections=total,
        pass_count=totals.get("pass_count") or 0,
        fail_count=totals.get("fail_count") or 0,
        manual_review_count=totals.get("review_count") or 0,
        pass_rate=round(((totals.get("pass_count") or 0) / total) * 100, 1)
        if total
        else 0.0,
        trend=trend,
        defect_distribution=[
            DefectCount(class_name=row["class_name"], count=row["count"])
            for row in defects
        ],
        recent=[_entry(row) for row in recent_rows],
        reference_checks=totals.get("reference_checks") or 0,
    )
