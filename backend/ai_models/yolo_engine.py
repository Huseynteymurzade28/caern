"""YOLOv8 detection engine (Strategy Pattern implementation)."""
from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from ai_models.base import BaseAIModel, Detection
from common_utils.config import settings
from common_utils.exceptions import GPUTimeoutError, ModelLoadError
from common_utils.logger import get_logger

log = get_logger(__name__)

CLASS_NAMES = {0: "bina", 1: "araç", 2: "ağaç", 3: "tarım_alanı"}


class YOLOEngine(BaseAIModel):
    """Ultralytics YOLOv8 object detector."""

    def __init__(self, model_path: Path | None = None) -> None:
        super().__init__(model_path or Path(settings.yolo_model_path))
        self._model = None

    def load(self) -> None:
        try:
            from ultralytics import YOLO
            self._model = YOLO(str(self.model_path))
            self._loaded = True
            log.info("yolo_loaded", path=str(self.model_path))
        except Exception as exc:
            raise ModelLoadError(f"YOLO modeli yüklenemedi: {exc}") from exc

    def predict(self, image: np.ndarray) -> List[Detection]:
        self._ensure_loaded()
        results = self._model.predict(
            source=image,
            conf=settings.model_confidence_threshold,
            verbose=False,
            device="cuda" if self._cuda_available() else "cpu",
        )
        detections: List[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                detections.append(
                    Detection(
                        bbox=xyxy,
                        confidence=conf,
                        class_id=cls_id,
                        class_name=CLASS_NAMES.get(cls_id, f"class_{cls_id}"),
                    )
                )
        log.debug("yolo_predict", detections=len(detections))
        return detections

    def get_metrics(self) -> dict:
        base = super().get_metrics()
        base["type"] = "yolov8"
        return base

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
