from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from hmi_yolo_311d_fsab.domain.io_points import IoDataType, IoDirection, IoPoint
from hmi_yolo_311d_fsab.presentation.status_indicator import StatusIndicator


class IoMonitor(QTableWidget):
    SIGNAL_COLUMN = 0
    DIRECTION_COLUMN = 1
    VALUE_COLUMN = 2
    QUALITY_COLUMN = 3
    TAG_COLUMN = 4
    TYPE_COLUMN = 5

    def __init__(self, points: tuple[IoPoint, ...], *, simulated: bool) -> None:
        super().__init__(len(points), 6)
        self.setObjectName("ioMonitor")
        self._boolean_indicators: dict[str, StatusIndicator] = {}
        self._logical_names: list[str] = []
        self.setHorizontalHeaderLabels(
            ["SEÑAL", "DIRECCIÓN", "ESTADO / VALOR", "CALIDAD", "TAG PLC", "TIPO"]
        )
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        for row, point in enumerate(points):
            self._logical_names.append(point.logical_name)
            direction = "ENTRADA" if point.direction is IoDirection.INPUT else "SALIDA"
            quality = "SIMULADA" if simulated else "SIN DATOS"
            displayed_value = "" if point.data_type is IoDataType.BOOLEAN else str(point.value)
            values = (
                point.logical_name.replace("_", " ").title(),
                direction,
                displayed_value,
                quality,
                point.tag,
                point.data_type.value,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                manual_output = column == self.VALUE_COLUMN and point.writable and simulated
                if not manual_output:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column == self.SIGNAL_COLUMN:
                    font = QFont(item.font())
                    font.setBold(True)
                    item.setFont(font)
                    item.setToolTip(f"Nombre lógico: {point.logical_name}")
                elif column == self.DIRECTION_COLUMN:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setForeground(
                        QColor("#38bdf8")
                        if point.direction is IoDirection.INPUT
                        else QColor("#f59e0b")
                    )
                    font = QFont(item.font())
                    font.setBold(True)
                    item.setFont(font)
                elif column in {self.VALUE_COLUMN, self.QUALITY_COLUMN, self.TYPE_COLUMN}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == self.QUALITY_COLUMN:
                    item.setForeground(QColor("#fbbf24" if simulated else "#94a3b8"))
                self.setItem(row, column, item)
            if point.data_type is IoDataType.BOOLEAN:
                indicator = StatusIndicator()
                indicator.setObjectName(f"ioIndicator_{point.logical_name}")
                indicator.setProperty("ioCell", True)
                indicator.setMinimumWidth(105)
                indicator.label.setObjectName("ioValueText")
                self._set_boolean_indicator(indicator, bool(point.value))
                self._boolean_indicators[point.logical_name] = indicator
                self.setCellWidget(row, self.VALUE_COLUMN, indicator)
            self.setRowHeight(row, 40)

        header = self.horizontalHeader()
        header.setSectionResizeMode(self.SIGNAL_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.DIRECTION_COLUMN, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.VALUE_COLUMN, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.QUALITY_COLUMN, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.TAG_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.TYPE_COLUMN, QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(80)
        self.setColumnWidth(self.DIRECTION_COLUMN, 110)
        self.setColumnWidth(self.VALUE_COLUMN, 135)
        self.setColumnWidth(self.QUALITY_COLUMN, 105)
        self.setColumnWidth(self.TYPE_COLUMN, 85)

    def update_values(self, values: dict[str, bool | int | float | str]) -> None:
        for row in range(self.rowCount()):
            logical_name = self._logical_names[row]
            if logical_name in values:
                value = values[logical_name]
                indicator = self._boolean_indicators.get(logical_name)
                if indicator is not None:
                    self.item(row, self.VALUE_COLUMN).setText("")
                    self._set_boolean_indicator(indicator, bool(value))
                else:
                    self.item(row, self.VALUE_COLUMN).setText(str(value))

    @staticmethod
    def _set_boolean_indicator(indicator: StatusIndicator, active: bool) -> None:
        indicator.setText("ON" if active else "OFF")
        indicator.set_active(active)
