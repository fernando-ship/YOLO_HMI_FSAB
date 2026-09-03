from pathlib import Path

import pytest

from hmi_yolo_311d_fsab.domain.inference import InferenceError, InferenceState
from hmi_yolo_311d_fsab.infrastructure.yolo_inference import YoloInferenceEngine


def test_yolo_engine_reports_missing_model() -> None:
    engine = YoloInferenceEngine(Path("missing-model.pt"), "cpu", 0.7, 640)

    with pytest.raises(InferenceError, match="No se encontro el modelo YOLO"):
        engine.start()

    assert engine.get_state() is InferenceState.ERROR
