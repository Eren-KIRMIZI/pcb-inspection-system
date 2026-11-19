"""Referans PCB ile incelenen görsel arasındaki SIFT/RANSAC hizalaması.

D2 kapsamında hizalama artık yalnızca ``matrix | None`` döndürmez; inlier
sayısı/oranı, ölçek, genel hizalama açısı ve güven kararı da döndürülür.
Güven eşiğinin altındaki homografiler ``trusted=False`` işaretlenir ve
karşılaştırma normalize koordinatlara düşer; karar motoru bunu MANUAL_REVIEW
olarak raporlar.

Önbellek anahtarı dosya yolu + mtime + boyuttur; referans görüntüsü
değiştirildiğinde eski homografi kullanılmaz.
"""

from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from ..config import settings


@dataclass(frozen=True)
class AlignmentResult:
    matrix: np.ndarray | None
    inlier_count: int
    inlier_ratio: float
    scale: float | None
    rotation_deg: float | None
    trusted: bool
    reason: str

    @property
    def ok(self) -> bool:
        """Güvenilir bir homografi varsa True."""

        return self.trusted and self.matrix is not None


def _failed(reason: str) -> AlignmentResult:
    return AlignmentResult(
        matrix=None,
        inlier_count=0,
        inlier_ratio=0.0,
        scale=None,
        rotation_deg=None,
        trusted=False,
        reason=reason,
    )


def _file_key(path: Path) -> tuple[str, int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return str(path.resolve()), stat.st_mtime_ns, stat.st_size


def _geometry(matrix: np.ndarray) -> tuple[float | None, float | None]:
    """Homografiden ölçek ve genel hizalama açısını çıkarır.

    Bu açı kartın hizalanması içindir; komponent rotasyonu ölçümü değildir.
    """

    try:
        scale = float(np.sqrt(abs(np.linalg.det(matrix[:2, :2]))))
        rotation = float(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0])))
    except (np.linalg.LinAlgError, ValueError):
        return None, None
    if not np.isfinite(scale) or not np.isfinite(rotation):
        return None, None
    return scale, rotation


def _compute(reference_path: Path, target_path: Path) -> AlignmentResult:
    reference = cv2.imread(str(reference_path), cv2.IMREAD_GRAYSCALE)
    target = cv2.imread(str(target_path), cv2.IMREAD_GRAYSCALE)
    if reference is None or target is None:
        return _failed("image_unreadable")

    sift = cv2.SIFT_create()
    key_ref, desc_ref = sift.detectAndCompute(reference, None)
    key_target, desc_target = sift.detectAndCompute(target, None)
    if (
        desc_ref is None
        or desc_target is None
        or len(key_ref) < 8
        or len(key_target) < 8
    ):
        return _failed("insufficient_keypoints")

    matcher = cv2.BFMatcher()
    pairs = matcher.knnMatch(desc_ref, desc_target, k=2)
    good: list[cv2.DMatch] = []
    for pair in pairs:
        if len(pair) < 2:
            continue
        first, second = pair
        if first.distance < settings.alignment_ratio_test * second.distance:
            good.append(first)
    if len(good) < 8:
        return _failed("insufficient_matches")

    source = np.float32([key_ref[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    destination = np.float32(
        [key_target[match.trainIdx].pt for match in good]
    ).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(
        source, destination, cv2.RANSAC, settings.alignment_ransac_threshold
    )
    if matrix is None or mask is None:
        return _failed("homography_failed")

    inlier_count = int(mask.sum())
    inlier_ratio = inlier_count / len(good)
    scale, rotation_deg = _geometry(matrix)
    result = AlignmentResult(
        matrix=matrix,
        inlier_count=inlier_count,
        inlier_ratio=round(inlier_ratio, 4),
        scale=round(scale, 4) if scale is not None else None,
        rotation_deg=round(rotation_deg, 2) if rotation_deg is not None else None,
        trusted=True,
        reason="ok",
    )

    if inlier_count < settings.alignment_min_inliers:
        return replace(result, trusted=False, reason="low_inlier_count")
    if inlier_ratio < settings.alignment_min_inlier_ratio:
        return replace(result, trusted=False, reason="low_inlier_ratio")
    if scale is not None and not (
        settings.alignment_min_scale <= scale <= settings.alignment_max_scale
    ):
        return replace(result, trusted=False, reason="implausible_scale")
    return result


@lru_cache(maxsize=settings.alignment_cache_size)
def _cached_alignment(
    reference_key: tuple[str, int, int],
    target_key: tuple[str, int, int],
) -> AlignmentResult:
    return _compute(Path(reference_key[0]), Path(target_key[0]))


def align_images(reference_path: Path, target_path: Path) -> AlignmentResult:
    """Referans görselden hedef görsele güvenilir homografi hesaplar.

    Sonuç ``ok`` ise ``matrix`` koordinat dönüşümü için kullanılabilir; aksi
    halde çağıran normalize koordinatlara devam etmelidir.
    """

    reference_key = _file_key(reference_path)
    target_key = _file_key(target_path)
    if reference_key is None or target_key is None:
        return _failed("image_unreadable")
    return _cached_alignment(reference_key, target_key)


def clear_alignment_cache() -> None:
    """Testler veya referans yeniden yükleme sonrası önbelleği temizler."""

    _cached_alignment.cache_clear()
