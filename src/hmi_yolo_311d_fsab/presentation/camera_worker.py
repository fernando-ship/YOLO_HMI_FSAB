import logging
from time import monotonic

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage

from hmi_yolo_311d_fsab.domain.camera import CameraError
from hmi_yolo_311d_fsab.domain.inference import InferenceError, InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionError, InspectionStatus
from hmi_yolo_311d_fsab.domain.plc import PlcError
from hmi_yolo_311d_fsab.domain.production import ProductionError
from hmi_yolo_311d_fsab.presentation.frame_renderer import frame_to_image, render_frame
from hmi_yolo_311d_fsab.services.hmi_service import HmiService


class CameraWorker(QObject):
    frame_ready = Signal(QImage, QImage, object)
    state_changed = Signal(object)
    operation_failed = Signal(str)
    inspection_failed = Signal(str)
    shutdown_completed = Signal()
    inspection_ready = Signal(object, object)
    counters_reset = Signal(object)
    production_cycle_ready = Signal(object, object)
    production_acknowledged = Signal(object, object)
    calibration_changed = Signal(bool)
    nok_evidence_ready = Signal(QImage, object)

    def __init__(
        self,
        hmi_service: HmiService,
        frames_per_second: int,
        maximum_frame_age_ms: int = 500,
    ) -> None:
        super().__init__()
        self._hmi_service = hmi_service
        self._interval_ms = round(1000 / min(frames_per_second, 15))
        self._timer: QTimer | None = None
        self._latest_result: InferenceResult | None = None
        self._latest_result_at: float | None = None
        self._maximum_frame_age_seconds = maximum_frame_age_ms / 1000
        self._logger = logging.getLogger(__name__)
        self._first_frame_reported = False
        self._calibration_mode = False
        self._latest_raw_image: QImage | None = None

    @Slot()
    def start_camera(self) -> None:
        try:
            state = self._hmi_service.start_camera()
            if self._timer is None:
                self._timer = QTimer(self)
                self._timer.timeout.connect(self._capture)
            self._timer.start(self._interval_ms)
        except (CameraError, InferenceError) as exc:
            self.operation_failed.emit(str(exc))
            return
        self.state_changed.emit(state)

    @Slot()
    def stop_camera(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        try:
            state = self._hmi_service.stop_camera()
        except CameraError as exc:
            self.operation_failed.emit(str(exc))
            return
        self.state_changed.emit(state)

    @Slot()
    def shutdown(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self.shutdown_completed.emit()

    @Slot()
    def inspect_latest(self) -> None:
        if self._latest_result is None:
            self.operation_failed.emit("No existe un frame disponible para inspeccionar")
            return
        try:
            if self._calibration_mode:
                result, counters = self._hmi_service.calibrate(self._latest_result)
            else:
                result, counters = self._hmi_service.inspect(self._latest_result)
        except InspectionError as exc:
            self.inspection_failed.emit(str(exc))
            return
        self.inspection_ready.emit(result, counters)
        if result.status is InspectionStatus.NOK and self._latest_raw_image is not None:
            self.nok_evidence_ready.emit(self._latest_raw_image.copy(), result)

    @Slot(bool)
    def set_calibration_mode(self, enabled: bool) -> None:
        self._calibration_mode = enabled
        self.calibration_changed.emit(enabled)

    @Slot()
    def reset_counters(self) -> None:
        self.counters_reset.emit(self._hmi_service.reset_inspection_counters())

    def set_maximum_frame_age(self, milliseconds: int) -> None:
        self._maximum_frame_age_seconds = milliseconds / 1000

    @Slot()
    def run_simulated_cycle(self) -> None:
        if self._latest_result is None:
            self.operation_failed.emit("No existe un frame disponible para el ciclo")
            return
        try:
            cycle, io_values = self._hmi_service.run_simulated_cycle(self._latest_result)
        except (ProductionError, InspectionError, PlcError) as exc:
            self.operation_failed.emit(str(exc))
            return
        self.production_cycle_ready.emit(cycle, io_values)
        if cycle.inspection.status is InspectionStatus.NOK and self._latest_raw_image is not None:
            self.nok_evidence_ready.emit(self._latest_raw_image.copy(), cycle.inspection)

    @Slot()
    def run_automatic_cycle(self) -> None:
        if self._latest_result is None or self._latest_result_at is None:
            self.inspection_failed.emit("Trigger rechazado: no existe un frame disponible")
            return
        age = monotonic() - self._latest_result_at
        if age > self._maximum_frame_age_seconds:
            self.inspection_failed.emit(
                f"Trigger rechazado: el frame tiene {age * 1000:.0f} ms de antiguedad"
            )
            return
        try:
            cycle, io_values = self._hmi_service.run_automatic_cycle(self._latest_result)
        except (ProductionError, InspectionError, PlcError) as exc:
            self.inspection_failed.emit(str(exc))
            return
        self.production_cycle_ready.emit(cycle, io_values)

    @Slot()
    def acknowledge_cycle(self) -> None:
        try:
            state, io_values = self._hmi_service.acknowledge_cycle()
        except (ProductionError, PlcError) as exc:
            self.operation_failed.emit(str(exc))
            return
        self.production_acknowledged.emit(state, io_values)

    @Slot()
    def _capture(self) -> None:
        try:
            frame = self._hmi_service.capture_frame()
            result = self._hmi_service.process_frame(frame)
            self._latest_result = result
            self._latest_result_at = monotonic()
        except (CameraError, InferenceError) as exc:
            if self._timer is not None:
                self._timer.stop()
            self._logger.exception("Fallo al capturar o procesar un frame")
            self.operation_failed.emit(str(exc))
            return
        if not self._first_frame_reported:
            self._logger.info(
                "Primer frame procesado: %d detecciones en %.1f ms",
                len(result.detections),
                result.elapsed_ms,
            )
            self._first_frame_reported = True
        raw_image = frame_to_image(frame)
        self._latest_raw_image = raw_image
        self.frame_ready.emit(render_frame(frame, result), raw_image, result)
