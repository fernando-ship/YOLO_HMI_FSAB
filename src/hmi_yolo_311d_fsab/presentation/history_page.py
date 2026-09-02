from datetime import date

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.inspection import StoredInspection


class HistoryPage(QWidget):
    export_requested = Signal(object)
    clear_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._records: tuple[StoredInspection, ...] = ()
        self.result_filter = QComboBox()
        self.result_filter.addItems(["Todos", "OK", "NOK"])
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setSpecialValueText("Todas las fechas")
        self.date_filter.setMinimumDate(QDate(2000, 1, 1))
        self.date_filter.setDate(self.date_filter.minimumDate())
        self.summary_label = QLabel("0 inspecciones | 0 B")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Fecha UTC", "Resultado", "Frame", "Duracion ms", "Origen", "Motivo"]
        )
        export_button = QPushButton("Exportar CSV")
        clear_button = QPushButton("Limpiar historial")
        self.result_filter.currentIndexChanged.connect(self._apply_filter)
        self.date_filter.dateChanged.connect(self._apply_filter)
        export_button.clicked.connect(self._request_export)
        clear_button.clicked.connect(self.clear_requested.emit)
        actions = QHBoxLayout()
        actions.addWidget(self.result_filter)
        actions.addWidget(self.date_filter)
        actions.addWidget(self.summary_label)
        actions.addStretch()
        actions.addWidget(export_button)
        actions.addWidget(clear_button)
        layout = QVBoxLayout(self)
        layout.addLayout(actions)
        layout.addWidget(self.table)

    def set_records(self, records: tuple[StoredInspection, ...], storage_bytes: int) -> None:
        self._records = records
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = (
                record.inspected_at.strftime("%Y-%m-%d %H:%M:%S"),
                record.status.value.upper(),
                str(record.frame_sequence),
                f"{record.elapsed_ms:.3f}",
                record.source.upper(),
                record.reason,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.summary_label.setText(
            f"{len(records)} inspecciones | {self._format_size(storage_bytes)}"
        )
        self.table.resizeColumnsToContents()
        self._apply_filter()

    def visible_records(self) -> tuple[StoredInspection, ...]:
        return tuple(
            record for row, record in enumerate(self._records) if not self.table.isRowHidden(row)
        )

    def _request_export(self) -> None:
        self.export_requested.emit(self.visible_records())

    def _apply_filter(self) -> None:
        desired_result = self.result_filter.currentText().lower()
        all_dates = self.date_filter.date() == self.date_filter.minimumDate()
        selected_date = date(
            self.date_filter.date().year(),
            self.date_filter.date().month(),
            self.date_filter.date().day(),
        )
        for row, record in enumerate(self._records):
            result_matches = desired_result == "todos" or record.status.value == desired_result
            date_matches = all_dates or record.inspected_at.date() == selected_date
            self.table.setRowHidden(row, not (result_matches and date_matches))

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        return f"{size / 1024:.1f} KiB"

