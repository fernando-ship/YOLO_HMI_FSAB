import importlib
import logging
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Any

from hmi_yolo_311d_fsab.domain.camera import CameraFrame
from hmi_yolo_311d_fsab.domain.inference import (
    BoundingBox,
    Detection,
    InferenceError,
    InferenceNotRunningError,
    InferenceResult,
    InferenceState,
)


class YoloInferenceEngine:
    """Adaptador opcional para modelos Ultralytics PT, ONNX y TensorRT."""

    def __init__(
        self, model_path: Path, device: str, iou_threshold: float, image_size: int
    ) -> None:
        self._model_path = model_path
        self._device = None if device == "auto" else device
        self._iou_threshold = iou_threshold
        self._image_size = image_size
        self._model: Any | None = None
        self._state = InferenceState.STOPPED
        self._lock = RLock()
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        with self._lock:
            if self._model is not None:
                self._state = InferenceState.RUNNING
                return
            if not self._model_path.is_file():
                self._state = InferenceState.ERROR
                raise InferenceError(f"No se encontro el modelo YOLO: {self._model_path}")
            try:
                ultralytics = importlib.import_module("ultralytics")
                self._model = ultralytics.YOLO(str(self._model_path))
                numpy = importlib.import_module("numpy")
                warmup_image = numpy.zeros(
                    (self._image_size, self._image_size, 3), dtype=numpy.uint8
                )
                self._model.predict(
                    source=warmup_image,
                    conf=0.01,
                    iou=self._iou_threshold,
                    imgsz=self._image_size,
                    device=self._device,
                    verbose=False,
                )
            except ModuleNotFoundError as exc:
                self._state = InferenceState.ERROR
                raise InferenceError(
                    "Ultralytics no esta instalado. Instale el extra de inferencia YOLO."
                ) from exc
            except Exception as exc:
                self._state = InferenceState.ERROR
                raise InferenceError(f"No fue posible cargar el modelo YOLO: {exc}") from exc
            self._state = InferenceState.RUNNING
            self._logger.info("Modelo YOLO cargado y calentado: %s", self._model_path)

    def stop(self) -> None:
        with self._lock:
            self._state = InferenceState.STOPPED

    def get_state(self) -> InferenceState:
        with self._lock:
            return self._state

    def infer(self, frame: CameraFrame, confidence_threshold: float) -> InferenceResult:
        with self._lock:
            if self._state is not InferenceState.RUNNING or self._model is None:
                raise InferenceNotRunningError("La inferencia YOLO no esta iniciada")
            try:
                numpy = importlib.import_module("numpy")
                rgb = numpy.frombuffer(frame.rgb_data, dtype=numpy.uint8).reshape(
                    frame.height, frame.width, 3
                )
                bgr = rgb[:, :, ::-1]
                started = perf_counter()
                results = self._model.predict(
                    source=bgr,
                    conf=confidence_threshold,
                    iou=self._iou_threshold,
                    imgsz=self._image_size,
                    device=self._device,
                    verbose=False,
                )
                elapsed_ms = (perf_counter() - started) * 1000
                detections = self._detections(results[0]) if results else ()
                return InferenceResult(frame.sequence, detections, elapsed_ms)
            except InferenceError:
                raise
            except Exception as exc:
                self._state = InferenceState.ERROR
                raise InferenceError(f"Fallo durante la inferencia YOLO: {exc}") from exc

    @staticmethod
    def _detections(result: Any) -> tuple[Detection, ...]:
        names = result.names
        parsed: list[Detection] = []
        for box in result.boxes:
            coordinates = box.xyxy[0].tolist()
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = (int(round(value)) for value in coordinates)
            parsed.append(
                Detection(
                    str(names[class_id]),
                    confidence,
                    BoundingBox(x1, y1, max(0, x2 - x1), max(0, y2 - y1)),
                )
            )
        return tuple(parsed)
