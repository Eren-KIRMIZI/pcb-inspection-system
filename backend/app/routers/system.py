from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter

from ..config import BASE_DIR, settings
from ..schemas import (
    ModelCard,
    ModelPerformance,
    ResourceStatus,
    SettingsResponse,
    SystemStatus,
)
from ..services.components import get_component_detector, is_component_detector_loaded
from ..services.detector import get_detector, is_detector_loaded
from ..services.evaluation import load_evaluation
from ..services.history import check_database

router = APIRouter(tags=["system"])

MEASURED_METRIC_LABELS = {
    "Precision",
    "Recall",
    "False positive / False negative",
    "Sınıf bazında precision / recall",
    "Uygulama içi mAP50 / mAP50-95",
}


def _class_names(detector: object) -> list[str]:
    model = getattr(detector, "model", None)
    names = getattr(model, "names", None)
    if isinstance(names, dict):
        return [str(value) for value in names.values()]
    return []


@router.get("/models", response_model=ModelPerformance)
def get_models() -> ModelPerformance:
    detector = get_detector()
    component_status = "active" if settings.component_model_path else "disabled"
    evaluation = load_evaluation()
    measured_in_app = evaluation is not None
    unmeasured_metrics = [
        metric
        for metric in (
            "Precision",
            "Recall",
            "Confusion matrix",
            "False positive / False negative",
            "Sınıf bazında precision / recall",
            "Uygulama içi mAP50 / mAP50-95",
        )
        if not measured_in_app or metric not in MEASURED_METRIC_LABELS
    ]
    defect_note = (
        "Metrikler model kartından alınmıştır; uygulama içinde yeniden ölçülmemiştir. "
        "Sınıf bazlı eşikler thresholds.json dosyasından uygulanır."
    )
    if measured_in_app:
        defect_note = (
            "Kart metrikleri model kartından alınmıştır; aynı modelin gerçek test split'i "
            "üzerindeki uygulama içi ölçümü ayrı panelde gösterilir. "
            "Sınıf bazlı eşikler thresholds.json dosyasından uygulanır."
        )

    models = [
        ModelCard(
            id="solder-defect",
            name=settings.defect_model_name,
            role="Lehim / montaj kusuru tespiti",
            status="active" if detector.engine == "real" else "configured",
            weights=settings.defect_model_name,
            map50=0.895,
            map50_95=0.657,
            source="Model kartı test seti (ParsaVictor/pcb-solder-defect-detection-yolo26)",
            classes=_class_names(detector),
            note=defect_note,
        ),
        ModelCard(
            id="component-detection",
            name=settings.component_model_name,
            role="Komponent konumu / türü (referans karşılaştırma)",
            status=component_status,
            weights=settings.component_model_name if settings.component_model_path else None,
            map50=0.432,
            source="Model kartı test seti (ParsaVictor/pcb-component-detection-yolo26)",
            classes=_class_names(get_component_detector())
            if settings.component_model_path
            else [],
            note=(
                "Düşük mAP50 nedeniyle yalnızca eşik üstü tespitler eşleştirmeye katılır. "
                "Bu model açı (rotation) bilgisi üretmez."
            ),
        ),
        ModelCard(
            id="bare-board",
            name="pcb-bare-board-defect-detection-yolo26",
            role="Çıplak kart iz / bakır kusurları",
            status="disabled",
            source="Model kartı (proje kapsamı dışı)",
            note="İndirilmedi ve etkinleştirilmedi; sonuç üretmez.",
        ),
    ]

    return ModelPerformance(
        measured_in_app=measured_in_app,
        evaluation=evaluation,
        models=models,
        unmeasured_metrics=unmeasured_metrics,
        limitations=[
            "solder_void sıklıkla insufficient_solder ile karışır.",
            "burn sınıfının recall değeri model kartına göre yaklaşık %62'dir.",
            "Koyu fotoğraflarda ve küçük komponentlerde doğruluk düşer.",
            "rotation_error, open_joint ve bilinmeyen anomali tespiti desteklenmez.",
            "RGB fotoğraf ile lehim altı void'leri güvenilir şekilde görülemez.",
        ],
    )


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else BASE_DIR / path


def _model_status(
    key: str,
    label: str,
    path: Path | None,
    loaded: bool,
    disabled_detail: str,
) -> ResourceStatus:
    if path is None:
        return ResourceStatus(key=key, label=label, status="warning", detail=disabled_detail)
    if not _resolve(path).exists():
        return ResourceStatus(key=key, label=label, status="error", detail="Model dosyası bulunamadı")
    if loaded:
        return ResourceStatus(key=key, label=label, status="ok", detail="Yüklendi · analiz hazır")
    return ResourceStatus(
        key=key,
        label=label,
        status="ok",
        detail="Dosya mevcut · ilk analizde yüklenecek",
    )


def _storage_status() -> ResourceStatus:
    try:
        for directory in (settings.upload_dir, settings.results_dir):
            directory.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=directory, prefix=".status-", delete=True):
                pass
    except OSError:
        return ResourceStatus(
            key="storage", label="Depolama", status="error", detail="Yazma izni yok"
        )
    return ResourceStatus(
        key="storage", label="Depolama", status="ok", detail="Yükleme ve rapor dizinleri yazılabilir"
    )


@router.get("/status", response_model=SystemStatus, tags=["system"])
def get_status() -> SystemStatus:
    """Model yüklemesi tetiklemeden gerçek sistem durumunu raporlar."""

    if settings.use_mock_detector:
        defect_model = ResourceStatus(
            key="defect_model",
            label="Kusur modeli",
            status="warning",
            detail="Mock motor aktif; gerçek model kullanılmıyor",
        )
    else:
        defect_model = _model_status(
            "defect_model", "Kusur modeli", settings.model_path, is_detector_loaded(),
            "Model yolu yapılandırılmadı",
        )
    component_model = _model_status(
        "component_model",
        "Komponent modeli",
        settings.component_model_path,
        is_component_detector_loaded(),
        "Referans karşılaştırması kapalı",
    )
    database_ok = check_database()
    return SystemStatus(
        api=ResourceStatus(key="api", label="API", status="ok", detail="Çevrimiçi"),
        defect_model=defect_model,
        component_model=component_model,
        storage=_storage_status(),
        database=ResourceStatus(
            key="database",
            label="Geçmiş veritabanı",
            status="ok" if database_ok else "error",
            detail="Erişilebilir" if database_ok else "Erişilemedi",
        ),
    )


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    detector = get_detector()
    return SettingsResponse(
        device=settings.device,
        engine=detector.engine,
        defect_model=settings.defect_model_name
        if detector.engine == "real"
        else detector.name,
        component_model=settings.component_model_name
        if settings.component_model_path
        else None,
        conf_threshold=settings.conf_threshold,
        fail_min_confidence=settings.fail_min_confidence,
        manual_review_min_confidence=settings.manual_review_min_confidence,
        class_thresholds_applied=getattr(detector, "thresholds_applied", False),
        detector_imgsz=settings.detector_imgsz,
        tiling_enabled=settings.tiling_enabled,
        tile_size=settings.tile_size,
        tile_overlap=settings.tile_overlap,
        tile_nms_iou=settings.tile_nms_iou,
        component_conf_threshold=settings.component_conf_threshold,
        component_imgsz=settings.component_imgsz,
        reference_component_min_confidence=settings.reference_component_min_confidence,
        reference_match_distance_ratio=settings.reference_match_distance_ratio,
        reference_shift_distance_ratio=settings.reference_shift_distance_ratio,
        min_image_width=settings.min_image_width,
        min_image_height=settings.min_image_height,
        max_upload_mb=settings.max_upload_mb,
    )
