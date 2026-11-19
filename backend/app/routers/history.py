from fastapi import APIRouter, HTTPException, Query, status

from ..schemas import HistoryEntry, InspectionResult, OverviewStats
from ..services.history import (
    count_results,
    get_result,
    list_results,
    overview,
)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/overview", response_model=OverviewStats)
def get_overview(
    days: int = Query(7, ge=1, le=365),
    date_from: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> OverviewStats:
    try:
        return overview(days=days, date_from=date_from, date_to=date_to)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[HistoryEntry])
def get_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    verdict: str | None = None,
    engine: str | None = None,
    search: str | None = None,
) -> list[HistoryEntry]:
    return list_results(
        limit=limit, offset=offset, verdict=verdict, engine=engine, search=search
    )


@router.get("/count")
def get_history_count(
    verdict: str | None = None,
    engine: str | None = None,
    search: str | None = None,
) -> dict[str, int]:
    return {
        "total": count_results(verdict=verdict, engine=engine, search=search)
    }


@router.get("/{image_id}", response_model=InspectionResult)
def get_inspection(image_id: str) -> InspectionResult:
    result = get_result(image_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analiz kaydı bulunamadı"
        )
    return InspectionResult.model_validate(result)
