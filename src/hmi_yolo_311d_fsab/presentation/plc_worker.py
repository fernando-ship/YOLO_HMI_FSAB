import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from hmi_yolo_311d_fsab.domain.inspection import InspectionError
from hmi_yolo_311d_fsab.domain.plc import PlcError
from hmi_yolo_311d_fsab.services.hmi_service import HmiService, HmiState

Operation = Callable[[], HmiState]


class PlcWorker(QObject):
    state_changed = Signal(object)
    operation_failed = Signal(str)
    shutdown_completed = Signal()
    io_updated = Signal(object)
    trigger_detected = Signal()
    result_ack_detected = Signal()
    simulated_input_changed = Signal(str, object)

    def __init__(self, hmi_service: HmiService, poll_interval_ms: int = 250) -> None:
        super().__init__()
        self._hmi_service = hmi_service
        self._logger = logging.getLogger(__name__)
        self._poll_timer: QTimer | None = None
        self._communication_failed = False
        self._poll_interval_ms = poll_interval_ms
        self._previous_trigger = False
        self._previous_ack = False

    @Slot()
    def connect_plc(self) -> None:
        self._run_operation(self._hmi_service.connect_plc)
        if self._hmi_service.get_state().plc_state.value == "connected":
            self._communication_failed = False
            self._previous_trigger = False
            self._previous_ack = False
            if self._poll_timer is None:
                self._poll_timer = QTimer(self)
                self._poll_timer.timeout.connect(self.poll_io)
            self._poll_timer.start(self._poll_interval_ms)

    @Slot()
    def disconnect_plc(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._run_operation(self._hmi_service.disconnect_plc)

    @Slot()
    def shutdown(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._hmi_service.stop()
        self.shutdown_completed.emit()

    @Slot()
    def poll_io(self) -> None:
        try:
            values = self._hmi_service.read_plc_snapshot()
        except PlcError as exc:
            if self._poll_timer is not None:
                self._poll_timer.stop()
            if not self._communication_failed:
                self._communication_failed = True
                self.operation_failed.emit(str(exc))
            return
        self.io_updated.emit(values)
        trigger = values.get("trigger_inspection") is True
        acknowledged = values.get("result_ack") is True
        if trigger and not self._previous_trigger:
            self.trigger_detected.emit()
        waiting_ack = self._hmi_service.get_state().production_state.value == "waiting_ack"
        if acknowledged and not self._previous_ack and waiting_ack:
            self.result_ack_detected.emit()
        self._previous_trigger = trigger
        self._previous_ack = acknowledged

    @Slot(str, object)
    def set_simulated_input(self, logical_name: str, value: object) -> None:
        if not isinstance(value, bool | str):
            self.operation_failed.emit("Tipo de entrada simulada no valido")
            return
        try:
            self._hmi_service.set_simulated_input(logical_name, value)
        except (InspectionError, PlcError) as exc:
            self.operation_failed.emit(str(exc))
            return
        self.simulated_input_changed.emit(logical_name, value)

    def _run_operation(self, operation: "Operation") -> None:
        try:
            state = operation()
        except PlcError as exc:
            self.operation_failed.emit(str(exc))
            return
        except Exception:
            self._logger.exception("Error inesperado en el worker PLC")
            self.operation_failed.emit("Se produjo un error interno inesperado")
            return
        self.state_changed.emit(state)
