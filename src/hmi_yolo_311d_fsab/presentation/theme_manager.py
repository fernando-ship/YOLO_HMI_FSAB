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
            Theme.DARK: (
                "#111827",
                "#1f2937",
                "#e5e7eb",
                "#374151",
                "#2563eb",
                "#18212f",
                "#92400e",
                "#f59e0b",
            ),
            Theme.LIGHT: (
                "#f3f4f6",
                "#ffffff",
                "#111827",
                "#d1d5db",
                "#2563eb",
                "#e8edf3",
                "#92400e",
                "#f59e0b",
            ),
            Theme.HIGH_CONTRAST: (
                "#000000",
                "#111111",
                "#ffffff",
                "#ffffff",
                "#ef233c",
                "#202020",
                "#991b1b",
                "#ff3347",
            ),
        }
        background, surface, text, border, accent, alternate, retry, retry_border = palettes[theme]
        return f"""
            QWidget {{ background: {background}; color: {text}; font-size: 14px; }}
            QListWidget, QPlainTextEdit, QTableWidget, QTabWidget::pane {{
                background: {surface}; border: 1px solid {border}; border-radius: 8px;
            }}
            QGroupBox {{ border: 1px solid {border}; border-radius: 8px; margin-top: 12px;
                padding: 12px 8px 8px 8px; font-weight: 600; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px;
                color: {accent}; font-size: 15px; font-weight: 700; }}
            QGroupBox[density="compact"] {{ padding: 7px 7px 5px 7px; }}
            QListWidget::item {{ padding: 14px 12px; margin: 3px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {accent}; color: white; }}
            QLabel#applicationTitle {{ font-size: 20px; font-weight: 700; }}
            QLabel#pageTitle {{ font-size: 18px; font-weight: 700; color: {accent}; }}
            QLabel#statusIndicatorText {{ font-size: 15px; font-weight: 600; }}
            QLabel#inspectionResult {{ font-size: 18px; font-weight: 700; }}
            QPushButton {{ background: {surface}; border: 1px solid {border};
                border-radius: 7px; padding: 9px 14px; }}
            QPushButton:hover {{ border-color: {accent}; }}
            QPushButton:pressed {{ background: {accent}; color: white; }}
            QPushButton[actionRole="start"] {{ background: #166534; border-color: #22c55e;
                color: white; font-weight: 600; }}
            QPushButton[actionRole="stop"] {{ background: #7f1d1d; border-color: #ef4444;
                color: white; font-weight: 600; }}
            QPushButton[actionRole="retry"] {{ background: {retry}; border-color: {retry_border};
                color: white; font-weight: 700; }}
            QPushButton[actionRole="primary"] {{ background: #1d4ed8; border-color: #60a5fa;
                color: white; font-weight: 700; }}
            QPushButton[actionRole="secondary"] {{ border-color: {accent};
                font-weight: 600; }}
            QPushButton[actionRole="utility"] {{ border-style: dashed; font-size: 13px; }}
            QPushButton:disabled {{ background: {surface}; color: #777777;
                border-color: #555555; }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {surface};
                border: 1px solid {border}; border-radius: 5px; padding: 6px; }}
            QTableWidget#ioMonitor {{ background: {surface};
                alternate-background-color: {alternate};
                border: 1px solid {border}; border-radius: 10px; }}
            QTableWidget#ioMonitor::item {{ padding: 7px; border-bottom: 1px solid {border}; }}
            QTableWidget#ioMonitor::item:selected {{ background: {accent}; color: white; }}
            QTableWidget#ioMonitor QWidget[ioCell="true"],
            QTableWidget#ioMonitor QWidget[ioCell="true"] QLabel {{ background: transparent; }}
            QLabel#ioValueText {{ font-size: 13px; font-weight: 700; }}
            QHeaderView::section {{ background: {surface}; padding: 9px; border: 0;
                border-bottom: 2px solid {accent}; font-size: 13px; font-weight: 700; }}
            QLabel#plcMessageBanner {{ border: 2px solid {accent}; border-radius: 7px;
                background: {surface}; color: {text}; font-weight: 700; }}
            QLabel#brandLogo {{ background: transparent; border: 0; }}
        """
