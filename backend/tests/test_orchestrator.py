"""JobOrchestrator unit tests with mocked AI/geo layers."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.mark.asyncio
async def test_nms_removes_duplicates():
    from analysis_engine.job_orchestrator import JobOrchestrator
    from ai_models.base import Detection

    dets = [
        Detection(bbox=[0, 0, 10, 10], confidence=0.9, class_id=0, class_name="bina"),
        Detection(bbox=[1, 1, 11, 11], confidence=0.7, class_id=0, class_name="bina"),
        Detection(bbox=[100, 100, 110, 110], confidence=0.8, class_id=1, class_name="araç"),
    ]
    result = JobOrchestrator._nms(dets, iou_threshold=0.5)
    # High-overlap pair should collapse to 1, far box stays
    assert len(result) == 2
    assert result[0].confidence == 0.9


def test_cancel_raises():
    from analysis_engine.job_orchestrator import JobOrchestrator
    from common_utils.exceptions import JobCancelledError

    orch = JobOrchestrator("job-1")
    orch.cancel()
    with pytest.raises(JobCancelledError):
        orch._check_cancelled()
