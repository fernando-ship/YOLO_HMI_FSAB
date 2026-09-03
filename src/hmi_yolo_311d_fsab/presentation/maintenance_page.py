from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from hmi_yolo_311d_fsab import __version__
from hmi_yolo_311d_fsab.domain.health import HealthSnapshot


class MaintenancePage(QWidget):
    def __init__(self, *, simulated_plc: bool, camera_backend: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"HMI_YOLO_311D_FSAB {__version__}"))
        plc_description = "simulado" if simulated_plc else "Omron NX"
        layout.addWidget(
            QLabel(
                f"PLC: {plc_description} | Camara: {camera_backend.upper()} | "
                "Inferencia: simulada"
            )
        )
        layout.addWidget(QLabel("Hardware real y herramientas de diagnostico: pendientes"))
        self.health_table = QTableWidget(0, 4)
        self.health_table.setHorizontalHeaderLabels(
            ["Componente", "Estado", "Detalle", "Ultimo heartbeat"]
        )
        layout.addWidget(self.health_table)
        layout.addStretch()

    def set_health(self, snapshots: tuple[HealthSnapshot, ...]) -> None:
        self.health_table.setRowCount(len(snapshots))
        for row, snapshot in enumerate(snapshots):
            heartbeat = (
                "--" if snapshot.last_heartbeat is None else f"{snapshot.last_heartbeat:.2f}"
            )
            values = (
                snapshot.component,
                snapshot.status.value.upper(),
                snapshot.message,
                heartbeat,
            )
            for column, value in enumerate(values):
                self.health_table.setItem(row, column, QTableWidgetItem(value))
        self.health_table.resizeColumnsToContents()
