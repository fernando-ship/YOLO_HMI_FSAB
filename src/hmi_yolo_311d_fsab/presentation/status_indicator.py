from enum import Enum

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class IndicatorState(Enum):
    OFF = "off"
    ON = "on"
    WARNING = "warning"
    ERROR = "error"


class StatusIndicator(QWidget):
    """Lampara circular para estados binarios, transitorios y de error."""

    OFF_COLOR = "#000000"
    ON_COLOR = "#39ff14"
    WARNING_COLOR = "#ffbf00"
    ERROR_COLOR = "#ff3131"

    def __init__(self, text: str = "", *, active: bool = False) -> None:
        super().__init__()
        self._state = IndicatorState.OFF
        self.lamp = QFrame()
        self.lamp.setObjectName("statusLamp")
        self.lamp.setFixedSize(18, 18)
        self.label = QLabel(text)
        self.label.setObjectName("statusIndicatorText")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.lamp)
        layout.addWidget(self.label, 1)
        self.set_active(active)

    def set_active(self, active: bool) -> None:
        self.set_state(IndicatorState.ON if active else IndicatorState.OFF)

    def set_state(self, state: IndicatorState) -> None:
        self._state = state
        colors = {
            IndicatorState.OFF: (self.OFF_COLOR, "#4b5563"),
            IndicatorState.ON: (self.ON_COLOR, "#d9ffd2"),
            IndicatorState.WARNING: (self.WARNING_COLOR, "#fff0a6"),
            IndicatorState.ERROR: (self.ERROR_COLOR, "#ffd1d1"),
        }
        color, border = colors[state]
        self.lamp.setStyleSheet(
            "QFrame#statusLamp {"
            f"background-color: {color};"
            f"border: 2px solid {border};"
            "border-radius: 9px;"
            "}"
        )
        descriptions = {
            IndicatorState.OFF: "Apagado",
            IndicatorState.ON: "Encendido",
            IndicatorState.WARNING: "En transicion",
            IndicatorState.ERROR: "Error",
        }
        description = descriptions[state]
        self.lamp.setAccessibleName(description)
        self.setAccessibleName(f"{self.text()}: {description}")

    def is_active(self) -> bool:
        return self._state is IndicatorState.ON

    def state(self) -> IndicatorState:
        return self._state

    def setText(self, text: str) -> None:  # noqa: N802
        self.label.setText(text)
        self.set_state(self._state)

    def text(self) -> str:
        return self.label.text()
