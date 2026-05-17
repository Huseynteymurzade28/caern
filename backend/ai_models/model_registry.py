"""Model Registry Singleton — each model loaded at most once."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Optional

from ai_models.base import BaseAIModel
from ai_models.yolo_engine import YOLOEngine
from ai_models.sam_engine import SAMEngine
from common_utils.logger import get_logger

log = get_logger(__name__)


class ModelRegistry:
    """Thread-safe singleton holding loaded model instances."""

    _instance: Optional["ModelRegistry"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "ModelRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._models: Dict[str, BaseAIModel] = {}
                cls._instance._model_lock = threading.Lock()
        return cls._instance

    def get_yolo(self, path: Path | None = None) -> YOLOEngine:
        key = f"yolo:{path or 'default'}"
        return self._get_or_create(key, lambda: YOLOEngine(path))  # type: ignore[return-value]

    def get_sam(self, path: Path | None = None) -> SAMEngine:
        key = f"sam:{path or 'default'}"
        return self._get_or_create(key, lambda: SAMEngine(path))  # type: ignore[return-value]

    def _get_or_create(self, key: str, factory) -> BaseAIModel:
        with self._model_lock:
            if key not in self._models:
                model = factory()
                model.load()
                self._models[key] = model
                log.info("model_registered", key=key)
        return self._models[key]

    def evict(self, key: str) -> None:
        with self._model_lock:
            self._models.pop(key, None)

    def loaded_models(self) -> list[str]:
        return list(self._models.keys())


registry = ModelRegistry()
