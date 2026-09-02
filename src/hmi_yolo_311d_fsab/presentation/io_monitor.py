from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from hmi_yolo_311d_fsab.domain.io_points import IoPoint


class IoMonitor(QTableWidget):
    def __init__(self, points: tuple[IoPoint, ...], *, simulated: bool) -> None:
        super().__init__(len(points), 6)
        self.setHorizontalHeaderLabels(["Punto", "Tag", "Tipo", "E/S", "Valor", "Calidad"])
        for row, point in enumerate(points):
            values = (
                point.logical_name,
                point.tag,
                point.data_type.value,
                point.direction.value.upper(),
                str(point.value),
                "SIMULADA" if simulated else "SIN DATOS",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                manual_output = column == 4 and point.writable and simulated
                if not manual_output:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.setItem(row, column, item)
        self.resizeColumnsToContents()

    def update_values(self, values: dict[str, bool | int | float | str]) -> None:
        for row in range(self.rowCount()):
            logical_name = self.item(row, 0).text()
            if logical_name in values:
                self.item(row, 4).setText(str(values[logical_name]))

