from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class EventsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.events = QPlainTextEdit()
        self.events.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.events)

    def append(self, message: str) -> None:
        self.events.appendPlainText(message)

