"""Segment Anything Model (SAM) segmentation engine."""
from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from ai_models.base import BaseAIModel, Detection
from common_utils.config import settings
from common_utils.exceptions import ModelLoadError
from common_utils.logger import get_logger

log = get_logger(__name__)


class SAMEngine(BaseAIModel):
    """Meta's Segment Anything Model for mask generation."""

    def __init__(self, model_path: Path | None = None) -> None:
        super().__init__(model_path or Path(settings.sam_model_path))
        self._predictor = None

    def load(self) -> None:
        try:
            from segment_anything import SamPredictor, sam_model_registry

            model_type = self._detect_model_type()
            device = "cuda" if self._cuda_available() else "cpu"
            sam = sam_model_registry[model_type](checkpoint=str(self.model_path))
            sam.to(device=device)
            self._predictor = SamPredictor(sam)
            self._loaded = True
            log.info("sam_loaded", path=str(self.model_path), device=device)
        except Exception as exc:
            raise ModelLoadError(f"SAM modeli yüklenemedi: {exc}") from exc

    def predict(self, image: np.ndarray) -> List[Detection]:
        """Generate masks for the entire image using automatic mask generation."""
        self._ensure_loaded()
        from segment_anything import SamAutomaticMaskGenerator

        generator = SamAutomaticMaskGenerator(
            self._predictor.model,
            pred_iou_thresh=settings.model_confidence_threshold,
        )
        masks = generator.generate(image)

        detections: List[Detection] = []
        for mask_data in masks:
            mask = mask_data["segmentation"]
            bbox = mask_data["bbox"]  # xywh
            confidence = float(mask_data["predicted_iou"])
            x, y, w, h = bbox
            detections.append(
                Detection(
                    bbox=[x, y, x + w, y + h],
                    confidence=confidence,
                    class_id=-1,
                    class_name="segment",
                    mask=mask,
                )
            )
        log.debug("sam_predict", segments=len(detections))
        return detections

    def predict_with_boxes(self, image: np.ndarray, boxes: list) -> List[Detection]:
        """Predict masks guided by bounding boxes from YOLO."""
        self._ensure_loaded()
        import torch

        self._predictor.set_image(image)
        input_boxes = torch.tensor(boxes, device=self._predictor.device)
        transformed = self._predictor.transform.apply_boxes_torch(
            input_boxes, image.shape[:2]
        )
        masks, scores, _ = self._predictor.predict_torch(
            point_coords=None,
            point_labels=None,
            boxes=transformed,
            multimask_output=False,
        )
        detections = []
        for i, (mask, score, box) in enumerate(zip(masks, scores, boxes)):
            detections.append(
                Detection(
                    bbox=box,
                    confidence=float(score[0]),
                    class_id=-1,
                    class_name="segment",
                    mask=mask[0].cpu().numpy(),
                )
            )
        return detections

    def _detect_model_type(self) -> str:
        name = self.model_path.name.lower()
        if "vit_h" in name:
            return "vit_h"
        if "vit_l" in name:
            return "vit_l"
        return "vit_b"

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
