from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class ConfigurationPage(QWidget):
    open_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        button = QPushButton("Abrir configuracion del sistema")
        button.clicked.connect(self.open_requested.emit)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Parametros de PLC, camara, inferencia, inspeccion y tags."))
        layout.addWidget(button)
        layout.addStretch()

