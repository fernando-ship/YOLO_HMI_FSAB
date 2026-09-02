import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from hmi_yolo_311d_fsab.domain.plc import PlcError
from hmi_yolo_311d_fsab.services.hmi_service import HmiService, HmiState

Operation = Callable[[], HmiState]


class PlcWorker(QObject):
    state_changed = Signal(object)
    operation_failed = Signal(str)
    shutdown_completed = Signal()
    io_updated = Signal(object)

    def __init__(self, hmi_service: HmiService) -> None:
        super().__init__()
        self._hmi_service = hmi_service
        self._logger = logging.getLogger(__name__)
        self._poll_timer: QTimer | None = None
        self._communication_failed = False

    @Slot()
    def connect_plc(self) -> None:
        self._run_operation(self._hmi_service.connect_plc)
        if self._hmi_service.get_state().plc_state.value == "connected":
            self._communication_failed = False
            if self._poll_timer is None:
                self._poll_timer = QTimer(self)
                self._poll_timer.timeout.connect(self.poll_io)
            self._poll_timer.start(250)

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

