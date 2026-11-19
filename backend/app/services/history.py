import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID

from ..config import settings
from ..schemas import (
    DefectCount,
    HistoryEntry,
    InspectionResult,
    OverviewPeriod,
    OverviewStats,
    PeriodComparison,
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


def _parse_day(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Geçersiz {field}: {value} (beklenen YYYY-MM-DD)") from exc


def _period_bounds(days: int, date_from: str | None, date_to: str | None) -> tuple[date, date]:
    start = _parse_day(date_from, "date_from")
    end = _parse_day(date_to, "date_to")
    today = datetime.now(timezone.utc).date()
    if start is None and end is None:
        end = today
        start = end - timedelta(days=days - 1)
    elif start is None:
        assert end is not None
        start = end - timedelta(days=days - 1)
    elif end is None:
        end = today
    assert start is not None and end is not None
    if start > end:
        raise ValueError("date_from, date_to değerinden sonra olamaz")
    return start, end


def _day_range(start: date, end: date) -> tuple[str, str]:
    return start.isoformat(), end.isoformat()


def _totals(connection: sqlite3.Connection, start: date, end: date) -> dict:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN verdict = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
               SUM(CASE WHEN verdict = 'FAIL' THEN 1 ELSE 0 END) AS fail_count,
               SUM(CASE WHEN verdict = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) AS review_count,
               SUM(defect_count) AS defect_count,
               SUM(CASE WHEN reference_name IS NOT NULL THEN 1 ELSE 0 END) AS reference_checks
        FROM inspections
        WHERE substr(created_at, 1, 10) BETWEEN ? AND ?
        """,
        _day_range(start, end),
    ).fetchone()
    return dict(row)


def _change(current: int, previous: int) -> tuple[int, float | None]:
    delta = current - previous
    return delta, round(delta / previous * 100, 1) if previous else None


def check_database() -> bool:
    """Geçmiş veritabanına erişilebilirliği doğrular (model yüklemez)."""
    try:
        with _connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False


def overview(
    days: int = 7,
    date_from: str | None = None,
    date_to: str | None = None,
    recent_limit: int = 8,
) -> OverviewStats:
    """Seçili dönemin gerçek istatistiklerini ve önceki dönem farkını döner."""

    start, end = _period_bounds(days, date_from, date_to)
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)

    with _connect() as connection:
        totals = _totals(connection, start, end)
        previous_totals = _totals(connection, prev_start, prev_end)
        all_time = int(
            connection.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
        )
        rows = connection.execute(
            """
            SELECT substr(created_at, 1, 10) AS day,
                   COUNT(*) AS total,
                   SUM(CASE WHEN verdict = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
                   SUM(CASE WHEN verdict = 'FAIL' THEN 1 ELSE 0 END) AS fail_count,
                   SUM(CASE WHEN verdict = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) AS review_count
            FROM inspections
            WHERE substr(created_at, 1, 10) BETWEEN ? AND ?
            GROUP BY day ORDER BY day
            """,
            _day_range(start, end),
        ).fetchall()
        defects = connection.execute(
            """
            SELECT d.class_name, COUNT(*) AS count
            FROM inspection_defects d
            JOIN inspections i ON i.image_id = d.image_id
            WHERE substr(i.created_at, 1, 10) BETWEEN ? AND ?
            GROUP BY d.class_name ORDER BY count DESC
            """,
            _day_range(start, end),
        ).fetchall()
        recent_rows = connection.execute(
            "SELECT * FROM inspections WHERE substr(created_at, 1, 10) BETWEEN ? AND ? "
            "ORDER BY created_at DESC LIMIT ?",
            (*_day_range(start, end), recent_limit),
        ).fetchall()

    trend_by_day = {row["day"]: row for row in rows}
    trend: list[TrendPoint] = []
    for index in range(length):
        day = (start + timedelta(days=index)).isoformat()
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
    defect_count = totals.get("defect_count") or 0
    previous_total = previous_totals.get("total") or 0
    previous_defects = previous_totals.get("defect_count") or 0
    total_delta, total_pct = _change(total, previous_total)
    defect_delta, defect_pct = _change(defect_count, previous_defects)

    return OverviewStats(
        total_inspections=total,
        all_time_count=all_time,
        pass_count=totals.get("pass_count") or 0,
        fail_count=totals.get("fail_count") or 0,
        manual_review_count=totals.get("review_count") or 0,
        pass_rate=round(((totals.get("pass_count") or 0) / total) * 100, 1)
        if total
        else 0.0,
        defect_count=defect_count,
        reference_checks=totals.get("reference_checks") or 0,
        period=OverviewPeriod(start=start.isoformat(), end=end.isoformat(), days=length),
        previous=PeriodComparison(
            total_inspections=previous_total,
            total_delta=total_delta,
            total_change_pct=total_pct,
            defect_count=previous_defects,
            defect_delta=defect_delta,
            defect_change_pct=defect_pct,
        ),
        trend=trend,
        defect_distribution=[
            DefectCount(class_name=row["class_name"], count=row["count"])
            for row in defects
        ],
        recent=[_entry(row) for row in recent_rows],
    )
