from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.camera import CameraState
from hmi_yolo_311d_fsab.domain.inference import InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionCounters, InspectionResult
from hmi_yolo_311d_fsab.domain.plc import ConnectionState
from hmi_yolo_311d_fsab.domain.production import ProductionCycleResult, ProductionState
from hmi_yolo_311d_fsab.presentation.status_indicator import IndicatorState, StatusIndicator
from hmi_yolo_311d_fsab.services.hmi_service import HmiState


class OperationPage(QWidget):
    connect_requested = Signal()
    disconnect_requested = Signal()
    camera_start_requested = Signal()
    camera_stop_requested = Signal()
    inspection_requested = Signal()
    counters_reset_requested = Signal()
    production_cycle_requested = Signal()
    production_acknowledge_requested = Signal()
    snapshot_requested = Signal()

    def __init__(self, initial_state: HmiState) -> None:
        super().__init__()
        self.page_title = QLabel("OPERACION")
        self.page_title.setObjectName("pageTitle")
        self.plc_state_label = StatusIndicator()
        self.camera_state_label = StatusIndicator()
        self.inference_state_label = QLabel()
        self.production_state_label = QLabel()
        self.detection_summary_label = QLabel("Objetos: 0 | Tiempo: -- ms")
        self.detection_summary_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.inference_state_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.counters_label = QLabel("Total: 0 | OK: 0 | NOK: 0")
        self.inspection_result_label = QLabel("INSPECCION: IDLE")
        self.inspection_result_label.setObjectName("inspectionResult")
        self.inspection_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inspection_result_label.setMinimumHeight(48)

        self.video_label = QLabel("Vista de camara detenida")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("background: #20252b; color: #d8dee9;")

        self.connect_button = QPushButton("Conectar")
        self.disconnect_button = QPushButton("Desconectar")
        self.camera_start_button = QPushButton("Iniciar")
        self.camera_stop_button = QPushButton("Detener")
        self.inspection_button = QPushButton("Inspeccion manual")
        self.reset_counters_button = QPushButton("Reiniciar")
        self.production_cycle_button = QPushButton("Trigger PLC")
        self.production_ack_button = QPushButton("Reconocer")
        self.snapshot_button = QPushButton("Capturar")
        self.snapshot_count_label = QLabel("Capturas: 0")
        self._snapshot_count = 0
        self.disconnect_button.setToolTip("Desconectar el PLC")
        self.camera_start_button.setToolTip("Iniciar la camara")
        self.camera_stop_button.setToolTip("Detener la camara")
        self.production_cycle_button.setToolTip("Simular un disparo recibido desde el PLC")
        self.production_ack_button.setToolTip(
            "Reconocer el resultado y preparar el siguiente ciclo"
        )
        self.reset_counters_button.setToolTip("Reiniciar los contadores OK/NOK")
        self.snapshot_button.setToolTip("Guardar el ultimo frame RGB sin anotaciones")

        equipment_layout = QGridLayout()
        equipment_layout.setSpacing(8)
        equipment_layout.addWidget(self.plc_state_label, 0, 0)
        equipment_layout.addWidget(self.connect_button, 0, 1)
        equipment_layout.addWidget(self.disconnect_button, 0, 2)
        equipment_layout.addWidget(self.camera_state_label, 1, 0)
        equipment_layout.addWidget(self.camera_start_button, 1, 1)
        equipment_layout.addWidget(self.camera_stop_button, 1, 2)
        equipment_layout.setColumnStretch(0, 1)
        self.equipment_group = QGroupBox("1. Preparar equipos")
        self.equipment_group.setProperty("density", "compact")
        self.equipment_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self.equipment_group.setLayout(equipment_layout)

        camera_layout = QVBoxLayout()
        camera_layout.addWidget(self.video_label, 1)
        camera_details = QHBoxLayout()
        camera_details.addWidget(self.detection_summary_label)
        camera_details.addWidget(self.inference_state_label)
        camera_details.addStretch()
        camera_details.addWidget(self.snapshot_count_label)
        camera_details.addWidget(self.snapshot_button)
        camera_layout.addLayout(camera_details)
        self.camera_group = QGroupBox("2. Verificar imagen")
        self.camera_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.camera_group.setLayout(camera_layout)

        inspection_summary = QHBoxLayout()
        self.counters_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.production_state_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        inspection_summary.addWidget(self.inspection_result_label, 2)
        inspection_summary.addWidget(self.counters_label)
        inspection_summary.addWidget(self.production_state_label)
        inspection_actions = QHBoxLayout()
        inspection_actions.addWidget(self.inspection_button)
        inspection_actions.addWidget(self.production_cycle_button)
        inspection_actions.addWidget(self.production_ack_button)
        inspection_actions.addStretch()
        inspection_actions.addWidget(self.reset_counters_button)
        inspection_layout = QVBoxLayout()
        inspection_layout.addLayout(inspection_summary)
        inspection_layout.addLayout(inspection_actions)
        self.inspection_group = QGroupBox("3. Inspeccionar y confirmar resultado")
        self.inspection_group.setProperty("density", "compact")
        self.inspection_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self.inspection_group.setLayout(inspection_layout)

        self._set_action_role(self.inspection_button, "primary")
        self._set_action_role(self.production_cycle_button, "primary")
        self._set_action_role(self.production_ack_button, "secondary")
        self._set_action_role(self.reset_counters_button, "utility")
        self._set_action_role(self.snapshot_button, "secondary")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self.page_title)
        layout.addWidget(self.equipment_group)
        layout.addWidget(self.camera_group, 5)
        layout.addWidget(self.inspection_group)

        self.connect_button.clicked.connect(self._show_plc_connecting)
        self.connect_button.clicked.connect(self.connect_requested.emit)
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)
        self.camera_start_button.clicked.connect(self._show_camera_starting)
        self.camera_start_button.clicked.connect(self.camera_start_requested.emit)
        self.camera_stop_button.clicked.connect(self.camera_stop_requested.emit)
        self.inspection_button.clicked.connect(self.inspection_requested.emit)
        self.reset_counters_button.clicked.connect(self.counters_reset_requested.emit)
        self.production_cycle_button.clicked.connect(self.production_cycle_requested.emit)
        self.production_ack_button.clicked.connect(self.production_acknowledge_requested.emit)
        self.snapshot_button.clicked.connect(self.snapshot_requested.emit)
        self.apply_state(initial_state)

    def apply_state(self, state: HmiState) -> None:
        self.plc_state_label.setText(f"PLC: {state.plc_state.value.upper()}")
        plc_indicator_states = {
            ConnectionState.DISCONNECTED: IndicatorState.OFF,
            ConnectionState.CONNECTING: IndicatorState.WARNING,
            ConnectionState.CONNECTED: IndicatorState.ON,
            ConnectionState.ERROR: IndicatorState.ERROR,
        }
        self.plc_state_label.set_state(plc_indicator_states[state.plc_state])
        self.camera_state_label.setText(f"CAMARA: {state.camera_state.value.upper()}")
        camera_indicator_states = {
            CameraState.STOPPED: IndicatorState.OFF,
            CameraState.RUNNING: IndicatorState.ON,
            CameraState.ERROR: IndicatorState.ERROR,
        }
        self.camera_state_label.set_state(camera_indicator_states[state.camera_state])
        self.inference_state_label.setText(
            f"INFERENCIA: {state.inference_state.value.upper()} (SIMULADA)"
        )
        self.production_state_label.setText(f"CICLO: {state.production_state.value.upper()}")
        self.connect_button.setEnabled(
            state.plc_state in {ConnectionState.DISCONNECTED, ConnectionState.ERROR}
        )
        plc_retry = state.plc_state is ConnectionState.ERROR
        self.connect_button.setText("Reintentar" if plc_retry else "Conectar")
        self._set_action_role(self.connect_button, "retry" if plc_retry else "start")
        self.disconnect_button.setEnabled(state.plc_state is ConnectionState.CONNECTED)
        self._set_action_role(self.disconnect_button, "stop")
        running = state.camera_state is CameraState.RUNNING
        self.camera_start_button.setEnabled(not running)
        camera_retry = state.camera_state is CameraState.ERROR
        self.camera_start_button.setText("Reintentar" if camera_retry else "Iniciar")
        self._set_action_role(self.camera_start_button, "retry" if camera_retry else "start")
        self.camera_stop_button.setEnabled(running)
        self._set_action_role(self.camera_stop_button, "stop")
        self.snapshot_button.setEnabled(running)
        inspection_unlocked = running and state.plc_state is ConnectionState.CONNECTED
        self.inspection_button.setEnabled(inspection_unlocked)
        self.inspection_button.setToolTip(
            "" if inspection_unlocked else "Conecte el PLC e inicie la camara para inspeccionar"
        )
        self.production_cycle_button.setEnabled(
            running
            and state.plc_state is ConnectionState.CONNECTED
            and state.production_state is ProductionState.WAITING_TRIGGER
        )
        self.production_ack_button.setEnabled(state.production_state is ProductionState.COMPLETED)

    def show_plc_error_state(self) -> None:
        self.plc_state_label.setText("PLC: ERROR")
        self.plc_state_label.set_state(IndicatorState.ERROR)
        self.connect_button.setText("Reintentar")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self._set_action_role(self.connect_button, "retry")

    def show_camera_error_state(self) -> None:
        self.camera_state_label.setText("CAMARA: ERROR")
        self.camera_state_label.set_state(IndicatorState.ERROR)
        self.camera_start_button.setText("Reintentar")
        self.camera_start_button.setEnabled(True)
        self.camera_stop_button.setEnabled(False)
        self._set_action_role(self.camera_start_button, "retry")
        self.snapshot_button.setEnabled(False)

    def show_snapshot_saved(self, path: str) -> None:
        self._snapshot_count += 1
        self.snapshot_count_label.setText(f"Capturas: {self._snapshot_count}")
        self.snapshot_count_label.setToolTip(path)

    def _show_plc_connecting(self) -> None:
        self.plc_state_label.setText("PLC: CONECTANDO")
        self.plc_state_label.set_state(IndicatorState.WARNING)
        self.connect_button.setEnabled(False)

    def _show_camera_starting(self) -> None:
        self.camera_state_label.setText("CAMARA: INICIANDO")
        self.camera_state_label.set_state(IndicatorState.WARNING)
        self.camera_start_button.setEnabled(False)

    @staticmethod
    def _set_action_role(button: QPushButton, role: str) -> None:
        button.setProperty("actionRole", role)
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def show_frame(self, image: QImage, result: InferenceResult) -> None:
        pixmap = QPixmap.fromImage(image).scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(pixmap)
        count = len(result.detections)
        details = ""
        if result.detections:
            detection = result.detections[0]
            details = f" | {detection.label}: {detection.confidence:.0%}"
        self.detection_summary_label.setText(
            f"Objetos: {count}{details} | Tiempo: {result.elapsed_ms:.2f} ms"
        )

    def show_inspection(self, result: InspectionResult, counters: InspectionCounters) -> None:
        self.inspection_result_label.setText(
            f"INSPECCION: {result.status.value.upper()} - {result.reason}"
        )
        color = "#16803c" if result.status.value == "ok" else "#b42318"
        self.inspection_result_label.setStyleSheet(
            f"background: {color}; color: white; font-weight: bold;"
        )
        self.show_counters(counters)

    def show_counters(self, counters: InspectionCounters) -> None:
        self.counters_label.setText(
            f"Total: {counters.total} | OK: {counters.accepted} | NOK: {counters.rejected}"
        )

    def show_production_cycle(self, cycle: ProductionCycleResult) -> None:
        self.show_inspection(cycle.inspection, cycle.counters)
        self.production_state_label.setText(f"CICLO: {cycle.state.value.upper()} #{cycle.sequence}")
        self.production_cycle_button.setEnabled(False)
        self.production_ack_button.setEnabled(True)

    def show_production_acknowledged(self, state: ProductionState) -> None:
        self.production_state_label.setText(f"CICLO: {state.value.upper()}")
        self.production_cycle_button.setEnabled(True)
        self.production_ack_button.setEnabled(False)

