import pytest

from hmi_yolo_311d_fsab.domain.camera import CameraFrame
from hmi_yolo_311d_fsab.domain.inference import (
    InferenceNotRunningError,
    InferenceState,
)
from hmi_yolo_311d_fsab.infrastructure.simulated_inference import SimulatedInferenceEngine
from hmi_yolo_311d_fsab.services.inference_service import InferenceService


def make_frame(sequence: int = 0) -> CameraFrame:
    return CameraFrame(100, 80, bytes(100 * 80 * 3), sequence)


def test_inference_requires_running_engine() -> None:
    engine = SimulatedInferenceEngine()
    with pytest.raises(InferenceNotRunningError):
        engine.infer(make_frame(), 0.5)


def test_detection_is_deterministic() -> None:
    engine = SimulatedInferenceEngine()
    engine.start()
    first = engine.infer(make_frame(3), 0.5)
    second = engine.infer(make_frame(3), 0.5)

    assert first == second
    assert first.detections[0].label == "pieza"
    assert first.detections[0].confidence == 0.92


def test_confidence_threshold_filters_detection() -> None:
    engine = SimulatedInferenceEngine()
    engine.start()
    assert engine.infer(make_frame(), 0.95).detections == ()


def test_inference_service_lifecycle() -> None:
    service = InferenceService(SimulatedInferenceEngine(), 0.5)
    assert service.start() is InferenceState.RUNNING
    assert len(service.process(make_frame()).detections) == 1
    assert service.stop() is InferenceState.STOPPED
