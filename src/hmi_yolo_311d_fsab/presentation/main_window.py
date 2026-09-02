from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QImage
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.alarm import Alarm
from hmi_yolo_311d_fsab.domain.health import HealthSnapshot
from hmi_yolo_311d_fsab.domain.inference import InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionCounters, InspectionResult
from hmi_yolo_311d_fsab.domain.io_points import IoPoint
from hmi_yolo_311d_fsab.domain.production import ProductionCycleResult, ProductionState
from hmi_yolo_311d_fsab.presentation.alarms_page import AlarmsPage
from hmi_yolo_311d_fsab.presentation.animations import fade_in
from hmi_yolo_311d_fsab.presentation.configuration_page import ConfigurationPage
from hmi_yolo_311d_fsab.presentation.events_page import EventsPage
from hmi_yolo_311d_fsab.presentation.history_page import HistoryPage
from hmi_yolo_311d_fsab.presentation.io_monitor import IoMonitor
from hmi_yolo_311d_fsab.presentation.maintenance_page import MaintenancePage
from hmi_yolo_311d_fsab.presentation.operation_page import OperationPage
from hmi_yolo_311d_fsab.services.hmi_service import HmiState


class MainWindow(QMainWindow):
    connect_requested = Signal()
    disconnect_requested = Signal()
    camera_start_requested = Signal()
    camera_stop_requested = Signal()
    inspection_requested = Signal()
    counters_reset_requested = Signal()
    settings_requested = Signal()
    production_cycle_requested = Signal()
    production_acknowledge_requested = Signal()
    closing = Signal()
    alarm_reported = Signal(str, str, str)
    alarm_acknowledge_requested = Signal(int)
    alarm_acknowledge_all_requested = Signal()

    def __init__(
        self,
        initial_state: HmiState,
        io_points: tuple[IoPoint, ...],
        *,
        reduced_motion: bool,
    ) -> None:
        super().__init__()
        self.setWindowTitle("HMI_YOLO_311D_FSAB")
        self.resize(1100, 820)
        self.operation_page = OperationPage(initial_state)
        self.io_monitor = IoMonitor(io_points, simulated=initial_state.simulated_plc)
        self.events_page = EventsPage()
        self.history_page = HistoryPage()
        self.configuration_page = ConfigurationPage()
        self.maintenance_page = MaintenancePage()
        self.alarms_page = AlarmsPage()
        self._reduced_motion = reduced_motion
        self.pages = QStackedWidget()
        for page in (
            self.operation_page,
            self.io_monitor,
            self.events_page,
            self.history_page,
            self.alarms_page,
            self.configuration_page,
            self.maintenance_page,
        ):
            self.pages.addWidget(page)

        self.navigation = QListWidget()
        self.navigation.addItems(
            [
                "Operacion",
                "Monitor I/O",
                "Eventos",
                "Historial",
                "Alarmas (0)",
                "Configuracion",
                "Mantenimiento",
            ]
        )
        self.navigation.setFixedWidth(170)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.currentRowChanged.connect(self._animate_current_page)
        self.navigation.setCurrentRow(0)
        content = QHBoxLayout()
        content.addWidget(self.navigation)
        content.addWidget(self.pages, 1)
        root = QVBoxLayout()
        self.message_banner = QLabel("Sin mensajes del PLC")
        self.message_banner.setObjectName("plcMessageBanner")
        self.message_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_banner.setMinimumHeight(38)
        plc_label = "PLC SIMULADO" if initial_state.simulated_plc else "OMRON NX ETHERNET/IP"
        root.addWidget(QLabel(f"HMI_YOLO_311D_FSAB  |  {plc_label}"))
        root.addWidget(self.message_banner)
        root.addLayout(content)
        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)
        self._forward_signals()
        self.configuration_page.open_requested.connect(self.settings_requested.emit)
        self.alarms_page.acknowledge_requested.connect(self.alarm_acknowledge_requested.emit)
        self.alarms_page.acknowledge_all_requested.connect(
            self.alarm_acknowledge_all_requested.emit
        )
        self.events_page.append(initial_state.message)
        self._publish_test_handles()

    def apply_state(self, state: HmiState) -> None:
        self.operation_page.apply_state(state)
        self.events_page.append(state.message)

    def show_frame(self, image: QImage, result: InferenceResult) -> None:
        self.operation_page.show_frame(image, result)

    def show_error(self, message: str) -> None:
        self.events_page.append(f"ERROR PLC: {message}")
        self.operation_page.connect_button.setEnabled(True)
        self.operation_page.disconnect_button.setEnabled(False)
        self.operation_page.plc_state_label.setText("PLC: ERROR")
        self.alarm_reported.emit("PLC", message, "error")

    def show_camera_error(self, message: str) -> None:
        self.events_page.append(f"ERROR DE CAMARA: {message}")
        self.operation_page.camera_start_button.setEnabled(True)
        self.operation_page.camera_stop_button.setEnabled(False)
        self.operation_page.camera_state_label.setText("CAMARA: ERROR")
        self.alarm_reported.emit("CAMARA", message, "error")

    def show_inspection_error(self, message: str) -> None:
        self.events_page.append(f"INSPECCION BLOQUEADA: {message}")
        self.operation_page.inspection_result_label.setText(message.upper())
        self.alarm_reported.emit("INTERLOCK PLC", message, "warning")

    def set_alarms(self, alarms: tuple[Alarm, ...], active_count: int) -> None:
        self.alarms_page.set_alarms(alarms)
        self.navigation.item(4).setText(f"Alarmas ({active_count})")

    def set_reduced_motion(self, reduced_motion: bool) -> None:
        self._reduced_motion = reduced_motion

    def set_health(self, snapshots: tuple[HealthSnapshot, ...]) -> None:
        self.maintenance_page.set_health(snapshots)

    def _animate_current_page(self) -> None:
        fade_in(self.pages.currentWidget(), reduced_motion=self._reduced_motion)

    def show_inspection(self, result: InspectionResult, counters: InspectionCounters) -> None:
        self.operation_page.show_inspection(result, counters)
        self.events_page.append(
            f"Inspeccion frame {result.frame_sequence}: {result.status.value.upper()}"
        )

    def show_counters(self, counters: InspectionCounters) -> None:
        self.operation_page.show_counters(counters)

    def show_configuration_saved(self) -> None:
        self.events_page.append(
            "Configuracion guardada. Reinicie la aplicacion para aplicar los cambios."
        )

    def show_production_cycle(
        self,
        cycle: ProductionCycleResult,
        io_values: dict[str, bool | int | float | str],
    ) -> None:
        self.operation_page.show_production_cycle(cycle)
        self.io_monitor.update_values(io_values)
        self.events_page.append(f"Handshake del ciclo {cycle.sequence} completado")

    def show_production_acknowledged(
        self,
        state: ProductionState,
        io_values: dict[str, bool | int | float | str],
    ) -> None:
        self.operation_page.show_production_acknowledged(state)
        self.io_monitor.update_values(io_values)

    def show_plc_snapshot(self, values: dict[str, bool | int | float | str]) -> None:
        self.io_monitor.update_values(values)
        message = values.get("operator_message", "")
        self.message_banner.setText(str(message) if message else "PLC conectado - sin mensajes")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.closing.emit()
        event.accept()

    def _forward_signals(self) -> None:
        pairs = (
            (self.operation_page.connect_requested, self.connect_requested),
            (self.operation_page.disconnect_requested, self.disconnect_requested),
            (self.operation_page.camera_start_requested, self.camera_start_requested),
            (self.operation_page.camera_stop_requested, self.camera_stop_requested),
            (self.operation_page.inspection_requested, self.inspection_requested),
            (self.operation_page.counters_reset_requested, self.counters_reset_requested),
            (self.operation_page.production_cycle_requested, self.production_cycle_requested),
            (
                self.operation_page.production_acknowledge_requested,
                self.production_acknowledge_requested,
            ),
        )
        for source, target in pairs:
            source.connect(target.emit)

    def _publish_test_handles(self) -> None:
        names = (
            "plc_state_label",
            "camera_state_label",
            "inference_state_label",
            "production_state_label",
            "detection_summary_label",
            "inspection_result_label",
            "counters_label",
            "video_label",
            "connect_button",
            "disconnect_button",
            "camera_start_button",
            "camera_stop_button",
            "inspection_button",
            "reset_counters_button",
            "production_cycle_button",
            "production_ack_button",
        )
        for name in names:
            setattr(self, name, getattr(self.operation_page, name))

