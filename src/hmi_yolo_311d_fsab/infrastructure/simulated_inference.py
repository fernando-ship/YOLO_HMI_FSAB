import logging
from threading import RLock

from hmi_yolo_311d_fsab.domain.camera import CameraFrame
from hmi_yolo_311d_fsab.domain.inference import (
    BoundingBox,
    Detection,
    InferenceNotRunningError,
    InferenceResult,
    InferenceState,
)


class SimulatedInferenceEngine:
    def __init__(self) -> None:
        self._state = InferenceState.STOPPED
        self._lock = RLock()
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        with self._lock:
            self._state = InferenceState.RUNNING
            self._logger.info("Motor de inferencia simulado iniciado")

    def stop(self) -> None:
        with self._lock:
            self._state = InferenceState.STOPPED
            self._logger.info("Motor de inferencia simulado detenido")

    def get_state(self) -> InferenceState:
        with self._lock:
            return self._state

    def infer(self, frame: CameraFrame, confidence_threshold: float) -> InferenceResult:
        with self._lock:
            if self._state is not InferenceState.RUNNING:
                raise InferenceNotRunningError("La inferencia no esta iniciada")
            confidence = 0.92
            detections: tuple[Detection, ...] = ()
            if confidence >= confidence_threshold:
                box_width = max(20, frame.width // 4)
                box_height = max(20, frame.height // 3)
                travel = max(1, frame.width - box_width)
                x = frame.sequence * 7 % travel
                y = max(0, (frame.height - box_height) // 2)
                detections = (
                    Detection(
                        label="pieza",
                        confidence=confidence,
                        box=BoundingBox(x, y, box_width, box_height),
                    ),
                )
            elapsed_ms = 2.0 + (frame.sequence % 4) * 0.25
            return InferenceResult(frame.sequence, detections, elapsed_ms)

