from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.camera import CameraState
from hmi_yolo_311d_fsab.domain.inference import InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionCounters, InspectionResult
from hmi_yolo_311d_fsab.domain.plc import ConnectionState
from hmi_yolo_311d_fsab.domain.production import ProductionCycleResult, ProductionState
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

    def __init__(self, initial_state: HmiState) -> None:
        super().__init__()
        self.plc_state_label = QLabel()
        self.camera_state_label = QLabel()
        self.inference_state_label = QLabel()
        self.production_state_label = QLabel()
        self.detection_summary_label = QLabel("Objetos: 0 | Tiempo: -- ms")
        self.counters_label = QLabel("Total: 0 | OK: 0 | NOK: 0")
        self.inspection_result_label = QLabel("INSPECCION: IDLE")
        self.inspection_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inspection_result_label.setMinimumHeight(64)

        self.video_label = QLabel("Vista de camara detenida")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("background: #20252b; color: #d8dee9;")

        self.connect_button = QPushButton("Conectar PLC")
        self.disconnect_button = QPushButton("Desconectar PLC")
        self.camera_start_button = QPushButton("Iniciar camara")
        self.camera_stop_button = QPushButton("Detener camara")
        self.inspection_button = QPushButton("Ejecutar inspeccion")
        self.reset_counters_button = QPushButton("Reiniciar contadores")
        self.production_cycle_button = QPushButton("Simular trigger PLC")
        self.production_ack_button = QPushButton("Reconocer resultado")

        status = QGridLayout()
        status.addWidget(self.plc_state_label, 0, 0)
        status.addWidget(self.camera_state_label, 0, 1)
        status.addWidget(self.inference_state_label, 1, 0)
        status.addWidget(self.production_state_label, 1, 1)

        plc_buttons = QHBoxLayout()
        plc_buttons.addWidget(self.connect_button)
        plc_buttons.addWidget(self.disconnect_button)
        camera_buttons = QHBoxLayout()
        camera_buttons.addWidget(self.camera_start_button)
        camera_buttons.addWidget(self.camera_stop_button)
        action_buttons = QHBoxLayout()
        action_buttons.addWidget(self.inspection_button)
        action_buttons.addWidget(self.production_cycle_button)
        action_buttons.addWidget(self.production_ack_button)
        action_buttons.addWidget(self.reset_counters_button)

        layout = QVBoxLayout(self)
        layout.addLayout(status)
        layout.addLayout(plc_buttons)
        layout.addWidget(self.video_label, 1)
        layout.addWidget(self.detection_summary_label)
        layout.addWidget(self.inspection_result_label)
        layout.addWidget(self.counters_label)
        layout.addLayout(camera_buttons)
        layout.addLayout(action_buttons)

        self.connect_button.clicked.connect(self.connect_requested.emit)
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)
        self.camera_start_button.clicked.connect(self.camera_start_requested.emit)
        self.camera_stop_button.clicked.connect(self.camera_stop_requested.emit)
        self.inspection_button.clicked.connect(self.inspection_requested.emit)
        self.reset_counters_button.clicked.connect(self.counters_reset_requested.emit)
        self.production_cycle_button.clicked.connect(self.production_cycle_requested.emit)
        self.production_ack_button.clicked.connect(self.production_acknowledge_requested.emit)
        self.apply_state(initial_state)

    def apply_state(self, state: HmiState) -> None:
        self.plc_state_label.setText(f"PLC: {state.plc_state.value.upper()}")
        self.camera_state_label.setText(f"CAMARA: {state.camera_state.value.upper()}")
        self.inference_state_label.setText(
            f"INFERENCIA: {state.inference_state.value.upper()} (SIMULADA)"
        )
        self.production_state_label.setText(f"CICLO: {state.production_state.value.upper()}")
        self.connect_button.setEnabled(
            state.plc_state in {ConnectionState.DISCONNECTED, ConnectionState.ERROR}
        )
        self.disconnect_button.setEnabled(state.plc_state is ConnectionState.CONNECTED)
        running = state.camera_state is CameraState.RUNNING
        self.camera_start_button.setEnabled(not running)
        self.camera_stop_button.setEnabled(running)
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

