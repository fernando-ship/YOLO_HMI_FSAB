import logging

from hmi_yolo_311d_fsab.domain.camera import CameraFrame
from hmi_yolo_311d_fsab.domain.inference import (
    InferenceEngine,
    InferenceError,
    InferenceResult,
    InferenceState,
)


class InferenceService:
    def __init__(self, engine: InferenceEngine, confidence_threshold: float) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("El umbral de confianza debe estar entre 0 y 1")
        self._engine = engine
        self._confidence_threshold = confidence_threshold
        self._logger = logging.getLogger(__name__)

    def start(self) -> InferenceState:
        try:
            self._engine.start()
        except InferenceError:
            raise
        except Exception as exc:
            self._logger.exception("Fallo inesperado al iniciar inferencia")
            raise InferenceError("No fue posible iniciar la inferencia") from exc
        return self._engine.get_state()

    def stop(self) -> InferenceState:
        try:
            self._engine.stop()
        except InferenceError:
            raise
        except Exception as exc:
            self._logger.exception("Fallo inesperado al detener inferencia")
            raise InferenceError("No fue posible detener la inferencia") from exc
        return self._engine.get_state()

    def get_state(self) -> InferenceState:
        return self._engine.get_state()

    def process(self, frame: CameraFrame) -> InferenceResult:
        return self._engine.infer(frame, self._confidence_threshold)
