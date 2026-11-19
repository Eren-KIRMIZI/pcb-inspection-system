"""AOI Engine 2.0 / adım 20: kusur çıkarımı için tiling yardımcıları.

Büyük PCB fotoğraflarında küçük kusurların kaçmaması için görsel örtüşen
tile'lara bölünür; her tile'ın YOLO kutuları orijinal görsel koordinatlarına
geri taşınır ve tile sınırlarında oluşan tekrarlar sınıf bazlı NMS ile temizlenir.
Bu modül yalnızca geometri ve birleştirme yapar; model çıkarımı ``detector.py``
içinde kalır. Sınıf eşikleri değiştirilmez.
"""

from dataclasses import dataclass

from ..schemas import Detection


@dataclass(frozen=True)
class Tile:
    x1: int
    y1: int
    x2: int
    y2: int


def generate_tiles(
    width: int, height: int, tile_size: int, overlap: float
) -> tuple[Tile, ...]:
    """Görseli örtüşen karelere böler; kenarlardaki küçük parçalar atlanır."""

    if width <= 0 or height <= 0 or tile_size <= 0:
        return ()
    clamped = min(max(overlap, 0.0), 0.9)
    stride = max(1, int(tile_size * (1.0 - clamped)))
    tiles: list[Tile] = []
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            x2 = min(x + tile_size, width)
            y2 = min(y + tile_size, height)
            if x2 - x < 16 or y2 - y < 16:
                continue
            tiles.append(Tile(x1=x, y1=y, x2=x2, y2=y2))
    return tuple(tiles)


def map_bbox(bbox: list[float], tile: Tile) -> list[float]:
    """Tile yerel kutusunu tam görsel koordinatlarına taşır."""

    return [
        bbox[0] + tile.x1,
        bbox[1] + tile.y1,
        bbox[2] + tile.x1,
        bbox[3] + tile.y1,
    ]


def iou(first: list[float], second: list[float]) -> float:
    """İki ``xyxy`` kutusunun kesişme/birleşme oranı."""

    ix1 = max(first[0], second[0])
    iy1 = max(first[1], second[1])
    ix2 = min(first[2], second[2])
    iy2 = min(first[3], second[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    area_first = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    area_second = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = area_first + area_second - intersection
    return intersection / union if union > 0 else 0.0


def nms_detections(
    detections: list[Detection], iou_threshold: float
) -> list[Detection]:
    """Sınıf bazlı, güven öncelikli NMS; sonuç deterministik sıralanır."""

    ordered = sorted(detections, key=lambda item: item.confidence, reverse=True)
    kept: list[Detection] = []
    while ordered:
        best = ordered.pop(0)
        kept.append(best)
        ordered = [
            item
            for item in ordered
            if item.class_name != best.class_name
            or iou(best.bbox, item.bbox) <= iou_threshold
        ]
    return sorted(kept, key=lambda item: (item.bbox[1], item.bbox[0], item.class_name))
