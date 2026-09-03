from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.alarm import Alarm


class AlarmsPage(QWidget):
    acknowledge_requested = Signal(int)
    acknowledge_all_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.filter = QComboBox()
        self.filter.addItems(["Todas", "Activas", "Reconocidas", "Resueltas"])
        self.filter.currentIndexChanged.connect(self._apply_filter)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Fecha UTC", "Origen", "Severidad", "Estado", "Mensaje"]
        )
        acknowledge = QPushButton("Reconocer seleccionada")
        acknowledge_all = QPushButton("Reconocer todas")
        acknowledge.clicked.connect(self._acknowledge_selected)
        acknowledge_all.clicked.connect(self.acknowledge_all_requested.emit)
        actions = QHBoxLayout()
        actions.addWidget(self.filter)
        actions.addWidget(acknowledge)
        actions.addWidget(acknowledge_all)
        layout = QVBoxLayout(self)
        layout.addLayout(actions)
        layout.addWidget(self.table)

    def set_alarms(self, alarms: tuple[Alarm, ...]) -> None:
        self.table.setRowCount(len(alarms))
        for row, alarm in enumerate(reversed(alarms)):
            values = (
                str(alarm.identifier),
                alarm.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                alarm.source,
                alarm.severity.value.upper(),
                alarm.state.value.upper(),
                alarm.message,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self._apply_filter()

    def _acknowledge_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.acknowledge_requested.emit(int(self.table.item(row, 0).text()))

    def _apply_filter(self) -> None:
        desired = self.filter.currentText()
        mapping = {"Activas": "ACTIVE", "Reconocidas": "ACKNOWLEDGED", "Resueltas": "RESOLVED"}
        for row in range(self.table.rowCount()):
            visible = desired == "Todas" or self.table.item(row, 4).text() == mapping[desired]
            self.table.setRowHidden(row, not visible)
