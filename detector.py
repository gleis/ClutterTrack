"""Object detection using YOLO11."""
from dataclasses import dataclass
from typing import List


@dataclass
class Detection:
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    x_center: float
    y_center: float


_model_cache = {}


def _get_model(model_name: str = "yolo11n.pt"):
    global _model_cache
    if model_name not in _model_cache:
        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError("ultralytics not installed. Run: pip install ultralytics")
        _model_cache[model_name] = YOLO(model_name)  # nano model, auto-downloads on first use
    return _model_cache[model_name]


def detect(image_path: str, conf_threshold: float = 0.25, model_name: str = "yolo11n.pt") -> List[Detection]:
    """Detect objects in an image using YOLO11.

    Returns a list of Detection objects with normalized coordinates [0, 1].
    """
    model = _get_model(model_name)
    results = model(image_path, conf=conf_threshold, verbose=False)

    detections = []
    for result in results:
        if result.boxes is None:
            continue

        img_h, img_w = result.orig_shape

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = result.names[cls_id]

            # Normalize to [0, 1]
            x_center = ((x1 + x2) / 2) / img_w
            y_center = ((y1 + y2) / 2) / img_h

            detections.append(Detection(
                label=label,
                confidence=conf,
                x1=x1 / img_w,
                y1=y1 / img_h,
                x2=x2 / img_w,
                y2=y2 / img_h,
                x_center=x_center,
                y_center=y_center,
            ))

    return detections
