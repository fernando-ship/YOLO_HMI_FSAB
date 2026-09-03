from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.camera import CameraState
from hmi_yolo_311d_fsab.domain.inference import InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionClassRule
from hmi_yolo_311d_fsab.services.hmi_service import HmiState


class CalibrationPage(QWidget):
    """Area independiente para probar vision sin intervenir el ciclo del PLC."""

    calibration_changed = Signal(bool)
    camera_start_requested = Signal()
    camera_stop_requested = Signal()
    snapshot_requested = Signal()

    def __init__(self, initial_state: HmiState) -> None:
        super().__init__()
        self._rules: tuple[InspectionClassRule, ...] = ()

        title = QLabel("CALIBRACION DE VISION")
        title.setObjectName("pageTitle")
        description = QLabel(
            "Pruebe la camara y el modelo YOLO sin conexion al PLC y sin modificar "
            "los contadores de produccion."
        )
        description.setWordWrap(True)

        self.calibration_mode = QCheckBox("Habilitar modo calibracion")
        self.calibration_mode.setChecked(False)
        self.status_label = QLabel("CALIBRACION DESACTIVADA")
        self.status_label.setObjectName("inspectionResult")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(48)

        self.start_button = QPushButton("Iniciar camara")
        self.stop_button = QPushButton("Detener camara")
        self.snapshot_button = QPushButton("Guardar muestra")
        controls = QHBoxLayout()
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.snapshot_button)
        controls.addStretch()

        self.video_label = QLabel("Active la calibracion e inicie la camara")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("background: #20252b; color: #d8dee9;")

        self.detection_label = QLabel("Objetos: 0 | Tiempo: -- ms")
        self.rules_table = QTableWidget(0, 4)
        self.rules_table.setHorizontalHeaderLabels(
            ["CLASE", "DETECTADOS", "CONFIANZA", "RESULTADO"]
        )
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.horizontalHeader().setStretchLastSection(True)

        camera_box = QGroupBox("Vista y diagnostico del modelo")
        camera_layout = QVBoxLayout(camera_box)
        camera_layout.addWidget(self.video_label, 1)
        camera_layout.addWidget(self.detection_label)
        camera_layout.addWidget(self.rules_table)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.calibration_mode)
        layout.addWidget(self.status_label)
        layout.addLayout(controls)
        layout.addWidget(camera_box, 1)

        self.calibration_mode.toggled.connect(self._mode_changed)
        self.start_button.clicked.connect(self.camera_start_requested.emit)
        self.stop_button.clicked.connect(self.camera_stop_requested.emit)
        self.snapshot_button.clicked.connect(self.snapshot_requested.emit)
        self.apply_state(initial_state)

    def set_mode(self, enabled: bool) -> None:
        self.calibration_mode.setChecked(enabled)

    def _mode_changed(self, enabled: bool) -> None:
        self.status_label.setText(
            "CALIBRACION ACTIVA - PLC OMITIDO" if enabled else "CALIBRACION DESACTIVADA"
        )
        self.calibration_changed.emit(enabled)

    def apply_state(self, state: HmiState) -> None:
        running = state.camera_state is CameraState.RUNNING
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.snapshot_button.setEnabled(running)

    def set_class_rules(self, rules: tuple[InspectionClassRule, ...]) -> None:
        self._rules = rules
        self.rules_table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            for column, value in enumerate((rule.label, "0", "--", "ESPERANDO")):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.rules_table.setItem(row, column, item)

    def show_frame(self, image: QImage, result: InferenceResult) -> None:
        self.video_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.detection_label.setText(
            f"Objetos: {len(result.detections)} | Tiempo: {result.elapsed_ms:.2f} ms"
        )
        for row, rule in enumerate(self._rules):
            matches = [
                item for item in result.detections
                if item.label == rule.label and item.confidence >= rule.minimum_confidence
            ]
            confidence = max((item.confidence for item in matches), default=0.0)
            passed = rule.minimum_objects <= len(matches) <= rule.maximum_objects
            self.rules_table.item(row, 1).setText(str(len(matches)))
            self.rules_table.item(row, 2).setText(
                f"{confidence:.0%} / minimo {rule.minimum_confidence:.0%}"
            )
            self.rules_table.item(row, 3).setText("CUMPLE" if passed else "NO CUMPLE")
