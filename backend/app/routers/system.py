from fastapi import APIRouter

from ..config import settings
from ..schemas import ModelCard, ModelPerformance, SettingsResponse
from ..services.components import get_component_detector
from ..services.detector import get_detector

router = APIRouter(tags=["system"])


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
            note=(
                "Metrikler model kartından alınmıştır; uygulama içinde yeniden ölçülmemiştir. "
                "Sınıf bazlı eşikler thresholds.json dosyasından uygulanır."
            ),
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
        measured_in_app=False,
        models=models,
        unmeasured_metrics=[
            "Precision",
            "Recall",
            "Confusion matrix",
            "False positive / False negative",
            "Sınıf bazında precision / recall",
            "Uygulama içi mAP50 / mAP50-95",
        ],
        limitations=[
            "solder_void sıklıkla insufficient_solder ile karışır.",
            "burn sınıfının recall değeri model kartına göre yaklaşık %62'dir.",
            "Koyu fotoğraflarda ve küçük komponentlerde doğruluk düşer.",
            "rotation_error, open_joint ve bilinmeyen anomali tespiti desteklenmez.",
            "RGB fotoğraf ile lehim altı void'leri güvenilir şekilde görülemez.",
        ],
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
        class_thresholds_applied=getattr(detector, "thresholds_applied", False),
        component_conf_threshold=settings.component_conf_threshold,
        component_imgsz=settings.component_imgsz,
        reference_component_min_confidence=settings.reference_component_min_confidence,
        reference_match_distance_ratio=settings.reference_match_distance_ratio,
        reference_shift_distance_ratio=settings.reference_shift_distance_ratio,
        min_image_width=settings.min_image_width,
        min_image_height=settings.min_image_height,
        max_upload_mb=settings.max_upload_mb,
    )
