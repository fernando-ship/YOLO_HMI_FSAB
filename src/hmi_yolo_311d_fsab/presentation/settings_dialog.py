from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.camera_device import CameraBackend, CaptureProfile
from hmi_yolo_311d_fsab.infrastructure.config import AppConfig, PlcMode
from hmi_yolo_311d_fsab.services.camera_discovery_service import CameraDiscoveryService


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, discovery_service: CameraDiscoveryService) -> None:
        super().__init__()
        self._config = config
        self._discovery_service = discovery_service
        self.setWindowTitle("Configuracion del sistema")
        self.resize(700, 520)
        tabs = QTabWidget()
        tabs.addTab(self._build_plc_tab(), "PLC")
        tabs.addTab(self._build_camera_tab(), "Camara")
        tabs.addTab(self._build_inference_tab(), "Inferencia")
        tabs.addTab(self._build_inspection_tab(), "Inspeccion")
        tabs.addTab(self._build_io_tab(), "Entradas / salidas")
        tabs.addTab(self._build_appearance_tab(), "Apariencia")
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def build_config(self) -> AppConfig:
        points = tuple(
            replace(point, tag=self.io_table.item(row, 1).text().strip())
            for row, point in enumerate(self._config.io_points)
        )
        return replace(
            self._config,
            plc=replace(
                self._config.plc,
                mode=PlcMode(self.plc_mode.currentData()),
                host=self.plc_host.text().strip(),
                port=self.plc_port.value(),
                timeout_seconds=self.plc_timeout.value(),
                reconnect_interval_seconds=self.plc_reconnect.value(),
                simulate_connection_error=self.plc_error.isChecked(),
            ),
            camera=replace(
                self._config.camera,
                backend=CameraBackend(self.camera_backend.currentData()),
                device=self.camera_device.currentData() or self.camera_device.currentText().strip(),
                sensor_id=self.camera_sensor_id.value(),
                profile=CaptureProfile(self.camera_profile.currentData()),
                width=self.camera_width.value(),
                height=self.camera_height.value(),
                frames_per_second=self.camera_fps.value(),
                pixel_format=self.camera_pixel_format.text().strip(),
                timeout_seconds=self.camera_timeout.value(),
                reconnect_interval_seconds=self.camera_reconnect.value(),
                buffer_count=self.camera_buffers.value(),
                rotation_degrees=int(self.camera_rotation.currentData()),
                horizontal_flip=self.camera_hflip.isChecked(),
                vertical_flip=self.camera_vflip.isChecked(),
                fallback_to_simulator=self.camera_fallback.isChecked(),
            ),
            inference=replace(
                self._config.inference,
                enabled=self.inference_enabled.isChecked(),
                confidence_threshold=self.inference_threshold.value(),
            ),
            inspection=replace(
                self._config.inspection,
                expected_label=self.expected_label.text().strip(),
                minimum_confidence=self.inspection_confidence.value(),
                minimum_objects=self.minimum_objects.value(),
                maximum_objects=self.maximum_objects.value(),
            ),
            io_points=points,
            appearance=replace(
                self._config.appearance,
                theme=self.theme.currentData(),
                reduced_motion=self.reduced_motion.isChecked(),
            ),
        )

    def _build_plc_tab(self) -> QWidget:
        self.plc_mode = QComboBox()
        self.plc_mode.addItem("Simulado", PlcMode.SIMULATED.value)
        self.plc_mode.addItem("Omron NX EtherNet/IP", PlcMode.REAL.value)
        self.plc_mode.setCurrentIndex(0 if self._config.plc.mode is PlcMode.SIMULATED else 1)
        self.plc_host = QLineEdit(self._config.plc.host)
        self.plc_port = self._spin(0, 65535, self._config.plc.port)
        self.plc_timeout = self._double_spin(0.1, 120.0, self._config.plc.timeout_seconds)
        self.plc_reconnect = self._double_spin(
            0.1, 3600.0, self._config.plc.reconnect_interval_seconds
        )
        self.plc_error = QCheckBox("Simular error de conexion")
        self.plc_error.setChecked(self._config.plc.simulate_connection_error)
        return self._form_widget(
            ("Modo", self.plc_mode),
            ("Direccion IP / host", self.plc_host),
            ("Puerto", self.plc_port),
            ("Timeout (s)", self.plc_timeout),
            ("Reconexion (s)", self.plc_reconnect),
            ("Pruebas", self.plc_error),
        )

    def _build_camera_tab(self) -> QWidget:
        self.camera_backend = QComboBox()
        for backend in CameraBackend:
            self.camera_backend.addItem(backend.value.upper(), backend.value)
        self.camera_backend.setCurrentText(self._config.camera.backend.value.upper())
        self.camera_device = QComboBox()
        self.camera_device.setEditable(True)
        self.camera_device.addItem(self._config.camera.device, self._config.camera.device)
        search_button = QPushButton("Buscar camaras")
        search_button.clicked.connect(self._discover_cameras)
        device_row = QWidget()
        device_layout = QHBoxLayout(device_row)
        device_layout.setContentsMargins(0, 0, 0, 0)
        device_layout.addWidget(self.camera_device)
        device_layout.addWidget(search_button)
        self.camera_discovery_status = QLabel("Sin busqueda")
        self.camera_sensor_id = self._spin(0, 15, self._config.camera.sensor_id)
        self.camera_profile = QComboBox()
        for profile in CaptureProfile:
            label = profile.value.replace("_", " ").title()
            self.camera_profile.addItem(label, profile.value)
        current_profile = self._config.camera.profile.value.replace("_", " ").title()
        self.camera_profile.setCurrentText(current_profile)
        self.camera_width = self._spin(16, 7680, self._config.camera.width)
        self.camera_height = self._spin(16, 4320, self._config.camera.height)
        self.camera_fps = self._spin(1, 60, self._config.camera.frames_per_second)
        self.camera_pixel_format = QLineEdit(self._config.camera.pixel_format)
        self.camera_timeout = self._double_spin(0.1, 120.0, self._config.camera.timeout_seconds)
        self.camera_reconnect = self._double_spin(
            0.1, 3600.0, self._config.camera.reconnect_interval_seconds
        )
        self.camera_buffers = self._spin(1, 32, self._config.camera.buffer_count)
        self.camera_rotation = QComboBox()
        for rotation in (0, 90, 180, 270):
            self.camera_rotation.addItem(f"{rotation} grados", rotation)
        self.camera_rotation.setCurrentText(f"{self._config.camera.rotation_degrees} grados")
        self.camera_hflip = QCheckBox("Volteo horizontal")
        self.camera_hflip.setChecked(self._config.camera.horizontal_flip)
        self.camera_vflip = QCheckBox("Volteo vertical")
        self.camera_vflip.setChecked(self._config.camera.vertical_flip)
        self.camera_fallback = QCheckBox("Usar simulador si falla la camara real")
        self.camera_fallback.setChecked(self._config.camera.fallback_to_simulator)
        return self._form_widget(
            ("Backend", self.camera_backend),
            ("Puerto / dispositivo", device_row),
            ("Deteccion", self.camera_discovery_status),
            ("Sensor CSI", self.camera_sensor_id),
            ("Perfil", self.camera_profile),
            ("Ancho", self.camera_width),
            ("Alto", self.camera_height),
            ("FPS", self.camera_fps),
            ("Formato", self.camera_pixel_format),
            ("Timeout (s)", self.camera_timeout),
            ("Reconexion (s)", self.camera_reconnect),
            ("Buffers", self.camera_buffers),
            ("Rotacion", self.camera_rotation),
            ("Orientacion", self.camera_hflip),
            ("Orientacion", self.camera_vflip),
            ("Respaldo", self.camera_fallback),
        )

    def _discover_cameras(self) -> None:
        devices = self._discovery_service.discover()
        previous = self.camera_device.currentText()
        self.camera_device.clear()
        for device in devices:
            self.camera_device.addItem(device.display_name, device.identifier)
        if devices:
            self.camera_device.setCurrentIndex(0)
            self.camera_discovery_status.setText(f"{len(devices)} camara(s) encontrada(s)")
        else:
            self.camera_device.addItem(previous, previous)
            self.camera_discovery_status.setText("No se encontraron camaras; use el simulador")

    def _build_inference_tab(self) -> QWidget:
        self.inference_enabled = QCheckBox("Inferencia habilitada")
        self.inference_enabled.setChecked(self._config.inference.enabled)
        self.inference_threshold = self._double_spin(
            0.0, 1.0, self._config.inference.confidence_threshold
        )
        return self._form_widget(
            ("Estado", self.inference_enabled),
            ("Umbral", self.inference_threshold),
        )

    def _build_inspection_tab(self) -> QWidget:
        self.expected_label = QLineEdit(self._config.inspection.expected_label)
        self.inspection_confidence = self._double_spin(
            0.0, 1.0, self._config.inspection.minimum_confidence
        )
        self.minimum_objects = self._spin(0, 100, self._config.inspection.minimum_objects)
        self.maximum_objects = self._spin(0, 100, self._config.inspection.maximum_objects)
        return self._form_widget(
            ("Clase esperada", self.expected_label),
            ("Confianza minima", self.inspection_confidence),
            ("Objetos minimos", self.minimum_objects),
            ("Objetos maximos", self.maximum_objects),
        )

    def _build_io_tab(self) -> QWidget:
        self.io_table = QTableWidget(len(self._config.io_points), 5)
        self.io_table.setHorizontalHeaderLabels(
            ["Nombre logico", "Tag / direccion", "Tipo", "Direccion", "Escritura"]
        )
        for row, point in enumerate(self._config.io_points):
            values = (
                point.logical_name,
                point.tag,
                point.data_type.value,
                point.direction.value,
                "Si" if point.writable else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column != 1:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.io_table.setItem(row, column, item)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.io_table)
        return widget

    def _build_appearance_tab(self) -> QWidget:
        self.theme = QComboBox()
        self.theme.addItem("Oscuro", "dark")
        self.theme.addItem("Claro", "light")
        self.theme.addItem("Alto contraste", "high_contrast")
        index = self.theme.findData(self._config.appearance.theme)
        self.theme.setCurrentIndex(index)
        self.reduced_motion = QCheckBox("Reducir animaciones")
        self.reduced_motion.setChecked(self._config.appearance.reduced_motion)
        return self._form_widget(
            ("Tema", self.theme),
            ("Accesibilidad", self.reduced_motion),
        )

    @staticmethod
    def _form_widget(*rows: tuple[str, QWidget]) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        for label, field in rows:
            layout.addRow(label, field)
        return widget

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        field = QSpinBox()
        field.setRange(minimum, maximum)
        field.setValue(value)
        return field

    @staticmethod
    def _double_spin(minimum: float, maximum: float, value: float) -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setRange(minimum, maximum)
        field.setDecimals(2)
        field.setValue(value)
        return field

