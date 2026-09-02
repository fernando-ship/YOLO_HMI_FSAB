from enum import Enum

from PySide6.QtWidgets import QApplication


class Theme(Enum):
    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high_contrast"


class ThemeManager:
    def apply(self, app: QApplication, theme: Theme) -> None:
        app.setStyleSheet(self._stylesheet(theme))

    @staticmethod
    def _stylesheet(theme: Theme) -> str:
        palettes = {
            Theme.DARK: ("#111827", "#1f2937", "#e5e7eb", "#374151", "#2563eb"),
            Theme.LIGHT: ("#f3f4f6", "#ffffff", "#111827", "#d1d5db", "#2563eb"),
            Theme.HIGH_CONTRAST: ("#000000", "#111111", "#ffffff", "#ffffff", "#ffff00"),
        }
        background, surface, text, border, accent = palettes[theme]
        return f"""
            QWidget {{ background: {background}; color: {text}; font-size: 14px; }}
            QListWidget, QPlainTextEdit, QTableWidget, QTabWidget::pane {{
                background: {surface}; border: 1px solid {border}; border-radius: 8px;
            }}
            QListWidget::item {{ padding: 14px 12px; margin: 3px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {accent}; color: white; }}
            QPushButton {{ background: {surface}; border: 1px solid {border};
                border-radius: 7px; padding: 9px 14px; }}
            QPushButton:hover {{ border-color: {accent}; }}
            QPushButton:pressed {{ background: {accent}; color: white; }}
            QPushButton:disabled {{ color: #777777; border-color: #555555; }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {surface};
                border: 1px solid {border}; border-radius: 5px; padding: 6px; }}
            QHeaderView::section {{ background: {surface}; padding: 7px; border: 0; }}
        """

