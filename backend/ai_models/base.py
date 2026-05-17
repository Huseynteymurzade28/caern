"""Abstract base for AI model strategies (Strategy Pattern)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np


@dataclass
class Detection:
    """Single detected object."""
    bbox: List[float]           # [x1, y1, x2, y2] in pixel coords
    confidence: float
    class_id: int
    class_name: str
    mask: np.ndarray | None = field(default=None, repr=False)


class BaseAIModel(ABC):
    """Strategy interface for object detection / segmentation models."""

    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory (GPU if available)."""

    @abstractmethod
    def predict(self, image: np.ndarray) -> List[Detection]:
        """Run inference on RGB HxWxC uint8 array."""

    def get_metrics(self) -> dict:
        return {"model": self.model_path.name, "loaded": self._loaded}

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
