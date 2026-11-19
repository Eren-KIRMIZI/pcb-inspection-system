"""AOI Engine 2.0 / adım 16: SIFT + RANSAC hizalama güveni ve önbelleği."""

import math
import os
from pathlib import Path

import cv2
import numpy as np

from backend.app.schemas import Detection, ReferenceBoard, ReferenceComponent
from backend.app.services.alignment import align_images, clear_alignment_cache
from backend.app.services.reference import compare_board


def _feature_image(path: Path, seed: int) -> np.ndarray:
    """SIFT için yeterli köşe içeren sentetik kart görseli üretir."""

    rng = np.random.default_rng(seed)
    image = np.full((240, 320, 3), 255, dtype=np.uint8)
    for _ in range(60):
        x, y = int(rng.integers(8, 300)), int(rng.integers(8, 220))
        width, height = int(rng.integers(4, 16)), int(rng.integers(4, 16))
        color = int(rng.integers(0, 130))
        cv2.rectangle(image, (x, y), (x + width, y + height), color, -1)
    cv2.imwrite(str(path), image)
    return image


def _warp(path: Path, image: np.ndarray, angle: float, scale: float) -> np.ndarray:
    center = (image.shape[1] / 2, image.shape[0] / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, scale)
    matrix[:, 2] += (6.0, -4.0)
    warped = cv2.warpAffine(image, matrix, (image.shape[1], image.shape[0]), borderValue=(255, 255, 255))
    cv2.imwrite(str(path), warped)
    return matrix


def test_alignment_recovers_rotation_and_scale(tmp_path: Path) -> None:
    clear_alignment_cache()
    reference = tmp_path / "reference.jpg"
    target = tmp_path / "target.jpg"
    image = _feature_image(reference, seed=7)
    expected = _warp(target, image, angle=8.0, scale=1.10)

    result = align_images(reference, target)

    assert result.ok, result.reason
    assert result.matrix is not None
    assert result.inlier_count >= 8
    assert result.inlier_ratio >= 0.35
    assert result.scale is not None and abs(result.scale - 1.10) < 0.05
    expected_rotation = math.degrees(math.atan2(expected[1, 0], expected[0, 0]))
    assert result.rotation_deg is not None
    assert abs(result.rotation_deg - expected_rotation) < 2.0
    assert result.reason == "ok"


def test_unrelated_images_are_not_trusted(tmp_path: Path) -> None:
    clear_alignment_cache()
    reference = tmp_path / "ref.jpg"
    target = tmp_path / "other.jpg"
    _feature_image(reference, seed=11)
    _feature_image(target, seed=99)

    result = align_images(reference, target)

    assert not result.ok
    assert result.reason in {
        "insufficient_keypoints",
        "insufficient_matches",
        "homography_failed",
        "low_inlier_count",
        "low_inlier_ratio",
        "implausible_scale",
    }


def test_uniform_image_has_no_features(tmp_path: Path) -> None:
    clear_alignment_cache()
    reference = tmp_path / "blank-ref.jpg"
    target = tmp_path / "blank-target.jpg"
    for path in (reference, target):
        cv2.imwrite(str(path), 255 * np.ones((120, 160, 3), dtype=np.uint8))

    result = align_images(reference, target)

    assert not result.ok
    assert result.reason == "insufficient_keypoints"
    assert result.matrix is None


def test_cache_key_tracks_file_changes(tmp_path: Path) -> None:
    clear_alignment_cache()
    reference = tmp_path / "ref.jpg"
    target = tmp_path / "target.jpg"
    image = _feature_image(reference, seed=21)
    _warp(target, image, angle=3.0, scale=1.0)

    first = align_images(reference, target)
    second = align_images(reference, target)
    assert first is second, "aynı dosyalar için önbellek kullanılmadı"

    _feature_image(target, seed=55)
    stat = target.stat()
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    third = align_images(reference, target)
    assert third is not first, "dosya değişmesine rağmen eski sonuç döndü"


def test_compare_board_exposes_alignment_details(tmp_path: Path) -> None:
    clear_alignment_cache()
    image_path = tmp_path / "board.jpg"
    _feature_image(image_path, seed=31)
    board = ReferenceBoard(
        name="alignment-test",
        image_path=str(image_path),
        components=[ReferenceComponent(ref="R1", type="resistor", x=0.5, y=0.5)],
    )
    detection = Detection(
        class_id=0,
        class_name="resistor",
        confidence=0.9,
        bbox=[150.0, 110.0, 170.0, 130.0],
    )

    check = compare_board(board, image_path, [detection])

    assert check.aligned is True
    assert check.alignment is not None
    assert check.alignment.trusted is True
    assert check.alignment.reason == "ok"
    assert check.alignment.inlier_count >= 8
    assert check.alignment.inlier_ratio >= 0.35
