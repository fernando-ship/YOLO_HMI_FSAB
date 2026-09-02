import logging

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage

from hmi_yolo_311d_fsab.domain.camera import CameraError
from hmi_yolo_311d_fsab.domain.inference import InferenceError, InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionError
from hmi_yolo_311d_fsab.domain.plc import PlcError
from hmi_yolo_311d_fsab.domain.production import ProductionError
from hmi_yolo_311d_fsab.presentation.frame_renderer import render_frame
from hmi_yolo_311d_fsab.services.hmi_service import HmiService


class CameraWorker(QObject):
    frame_ready = Signal(QImage, object)
    state_changed = Signal(object)
    operation_failed = Signal(str)
    inspection_failed = Signal(str)
    shutdown_completed = Signal()
    inspection_ready = Signal(object, object)
    counters_reset = Signal(object)
    production_cycle_ready = Signal(object, object)
    production_acknowledged = Signal(object, object)

    def __init__(self, hmi_service: HmiService, frames_per_second: int) -> None:
        super().__init__()
        self._hmi_service = hmi_service
        self._interval_ms = round(1000 / frames_per_second)
        self._timer: QTimer | None = None
        self._latest_result: InferenceResult | None = None
        self._logger = logging.getLogger(__name__)

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
            result, counters = self._hmi_service.inspect(self._latest_result)
        except InspectionError as exc:
            self.inspection_failed.emit(str(exc))
            return
        self.inspection_ready.emit(result, counters)

    @Slot()
    def reset_counters(self) -> None:
        self.counters_reset.emit(self._hmi_service.reset_inspection_counters())

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
        except (CameraError, InferenceError) as exc:
            if self._timer is not None:
                self._timer.stop()
            self.operation_failed.emit(str(exc))
            return
        self.frame_ready.emit(render_frame(frame, result), result)

