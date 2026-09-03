from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.io_points import IoDataType, IoDirection, IoPoint


class PlcSimulatorPage(QWidget):
    input_requested = Signal(str, object)
    pulse_requested = Signal(str)

    def __init__(self, points: tuple[IoPoint, ...], *, enabled: bool) -> None:
        super().__init__()
        title = QLabel("SIMULADOR DE PLC")
        title.setObjectName("pageTitle")
        warning = QLabel(
            "Controles disponibles solo para el PLC simulado. Las salidas son de solo lectura."
        )
        self._input_checks: dict[str, QCheckBox] = {}
        self._output_labels: dict[str, QLabel] = {}
        grid = QGridLayout()
        grid.addWidget(QLabel("Entrada"), 0, 0)
        grid.addWidget(QLabel("Tag"), 0, 1)
        grid.addWidget(QLabel("Valor"), 0, 2)
        row = 1
        for point in points:
            if (
                point.direction is not IoDirection.INPUT
                or point.data_type is not IoDataType.BOOLEAN
            ):
                continue
            check = QCheckBox()
            check.setEnabled(enabled)
            check.toggled.connect(
                lambda checked, name=point.logical_name: self.input_requested.emit(name, checked)
            )
            self._input_checks[point.logical_name] = check
            grid.addWidget(QLabel(point.logical_name), row, 0)
            grid.addWidget(QLabel(point.tag), row, 1)
            grid.addWidget(check, row, 2)
            if point.logical_name in {"trigger_inspection", "result_ack"}:
                pulse = QPushButton("Pulso")
                pulse.setEnabled(enabled)
                pulse.clicked.connect(
                    lambda _checked=False, name=point.logical_name: self.pulse_requested.emit(name)
                )
                grid.addWidget(pulse, row, 3)
            row += 1
        self.message = QLineEdit()
        self.message.setEnabled(enabled)
        send = QPushButton("Enviar al banner")
        send.setEnabled(enabled)
        send.clicked.connect(
            lambda: self.input_requested.emit("operator_message", self.message.text())
        )
        grid.addWidget(QLabel("operator_message"), row, 0)
        grid.addWidget(self.message, row, 1, 1, 2)
        grid.addWidget(send, row, 3)
        row += 1
        grid.addWidget(QLabel("Salidas HMI"), row, 0, 1, 4, Qt.AlignmentFlag.AlignCenter)
        row += 1
        for point in points:
            if point.direction is not IoDirection.OUTPUT:
                continue
            value = QLabel(str(point.value))
            self._output_labels[point.logical_name] = value
            grid.addWidget(QLabel(point.logical_name), row, 0)
            grid.addWidget(QLabel(point.tag), row, 1)
            grid.addWidget(value, row, 2)
            row += 1
        content = QWidget()
        content.setLayout(grid)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(warning)
        layout.addWidget(scroll)

    def update_values(self, values: dict[str, bool | int | float | str]) -> None:
        for name, check in self._input_checks.items():
            check.blockSignals(True)
            check.setChecked(values.get(name) is True)
            check.blockSignals(False)
        for name, label in self._output_labels.items():
            if name in values:
                label.setText(str(values[name]))
        message = values.get("operator_message")
        if isinstance(message, str) and not self.message.hasFocus():
            self.message.setText(message)
