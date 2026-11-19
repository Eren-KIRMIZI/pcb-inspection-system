from pathlib import Path

import cv2
import numpy as np


def align_images(reference_path: Path, target_path: Path) -> np.ndarray | None:
    """Referans görselden hedef görsele SIFT homografisi hesaplar.

    Yeterli eşleşme bulunamazsa None döner; karşılaştırma normalize koordinatlarla devam eder.
    """

    reference = cv2.imread(str(reference_path), cv2.IMREAD_GRAYSCALE)
    target = cv2.imread(str(target_path), cv2.IMREAD_GRAYSCALE)
    if reference is None or target is None:
        return None

    sift = cv2.SIFT_create()
    key_ref, desc_ref = sift.detectAndCompute(reference, None)
    key_target, desc_target = sift.detectAndCompute(target, None)
    if desc_ref is None or desc_target is None:
        return None
    if len(key_ref) < 8 or len(key_target) < 8:
        return None

    matcher = cv2.BFMatcher()
    pairs = matcher.knnMatch(desc_ref, desc_target, k=2)
    good = [
        first
        for first, second in pairs
        if first.distance < 0.75 * second.distance
    ]
    if len(good) < 8:
        return None

    source = np.float32([key_ref[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    destination = np.float32([key_target[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(source, destination, cv2.RANSAC, 5.0)
    if matrix is None or mask is None or int(mask.sum()) < 8:
        return None
    return matrix
