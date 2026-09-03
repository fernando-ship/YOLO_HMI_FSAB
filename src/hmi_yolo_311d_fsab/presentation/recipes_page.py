from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hmi_yolo_311d_fsab.domain.inspection import InspectionClassRule
from hmi_yolo_311d_fsab.domain.recipe import InspectionRecipe


class RecipesPage(QWidget):
    save_requested = Signal(object)
    activate_requested = Signal(str)
    duplicate_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._recipes: dict[str, InspectionRecipe] = {}
        self.title = QLabel("RECETAS DE INSPECCION")
        self.title.setObjectName("pageTitle")
        self.active_label = QLabel("Activa: --")
        self.list = QListWidget()
        self.identifier = QLineEdit()
        self.name = QLineEdit()
        self.expected_label = QLineEdit()
        self.confidence = self._double(0, 1)
        self.minimum_objects = self._spin(0, 100)
        self.maximum_objects = self._spin(0, 100)
        self.quality = self._double(0, 100)
        self.timeout = self._double(0.1, 120)
        self.frame_age = self._spin(50, 10000)
        self.class_rules = QTableWidget(3, 5)
        self.class_rules.setHorizontalHeaderLabels(
            ["Usar", "Clase", "Confianza", "Minimo", "Maximo"]
        )
        self._set_class_rules(())
        form = QFormLayout()
        for label, field in (
            ("Identificador", self.identifier),
            ("Nombre", self.name),
            ("Clase esperada", self.expected_label),
            ("Confianza minima", self.confidence),
            ("Objetos minimos", self.minimum_objects),
            ("Objetos maximos", self.maximum_objects),
            ("Calidad minima (%)", self.quality),
            ("Timeout (s)", self.timeout),
            ("Frame maximo (ms)", self.frame_age),
        ):
            form.addRow(label, field)
        save = QPushButton("Guardar")
        activate = QPushButton("Activar")
        duplicate = QPushButton("Duplicar")
        delete = QPushButton("Eliminar")
        actions = QHBoxLayout()
        for button in (save, activate, duplicate, delete):
            actions.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.active_label)
        layout.addWidget(self.list)
        layout.addLayout(form)
        layout.addWidget(QLabel("REQUISITOS POR CLASE"))
        layout.addWidget(self.class_rules)
        layout.addLayout(actions)
        self.list.currentRowChanged.connect(self._load_selected)
        save.clicked.connect(lambda: self.save_requested.emit(self._build()))
        activate.clicked.connect(lambda: self.activate_requested.emit(self.identifier.text()))
        duplicate.clicked.connect(lambda: self.duplicate_requested.emit(self.identifier.text()))
        delete.clicked.connect(lambda: self.delete_requested.emit(self.identifier.text()))

    def set_recipes(self, recipes: tuple[InspectionRecipe, ...], active: InspectionRecipe) -> None:
        selected = self.identifier.text()
        self._recipes = {item.identifier: item for item in recipes}
        self.list.clear()
        for recipe in recipes:
            self.list.addItem(
                f"{'● ' if recipe.identifier == active.identifier else ''}{recipe.name}"
            )
            self.list.item(self.list.count() - 1).setData(256, recipe.identifier)
        self.active_label.setText(f"Activa: {active.name}")
        index = next((i for i, item in enumerate(recipes) if item.identifier == selected), 0)
        self.list.setCurrentRow(index)

    def _load_selected(self, row: int) -> None:
        if row < 0:
            return
        recipe = self._recipes[str(self.list.item(row).data(256))]
        self.identifier.setText(recipe.identifier)
        self.name.setText(recipe.name)
        self.expected_label.setText(recipe.expected_label)
        self.confidence.setValue(recipe.minimum_confidence)
        self.minimum_objects.setValue(recipe.minimum_objects)
        self.maximum_objects.setValue(recipe.maximum_objects)
        self.quality.setValue(recipe.quality_threshold_percent)
        self.timeout.setValue(recipe.cycle_timeout_seconds)
        self.frame_age.setValue(recipe.maximum_frame_age_ms)
        self._set_class_rules(recipe.class_rules)

    def _build(self) -> InspectionRecipe:
        return InspectionRecipe(
            self.identifier.text().strip(),
            self.name.text().strip(),
            self.expected_label.text().strip(),
            self.confidence.value(),
            self.minimum_objects.value(),
            self.maximum_objects.value(),
            self.quality.value(),
            self.timeout.value(),
            self.frame_age.value(),
            self._build_class_rules(),
        )

    def _set_class_rules(self, rules: tuple[InspectionClassRule, ...]) -> None:
        existing = {rule.label: rule for rule in rules}
        labels = ["Bolsa", "Label", "QR CODE"]
        labels.extend(label for label in existing if label not in labels)
        self.class_rules.setRowCount(len(labels))
        for row, label in enumerate(labels):
            rule = existing.get(label, InspectionClassRule(label, 0.70, 1, 1, True))
            enabled = QCheckBox()
            enabled.setChecked(rule.enabled)
            self.class_rules.setCellWidget(row, 0, enabled)
            label_item = QTableWidgetItem(rule.label)
            confidence = self._double(0, 1)
            confidence.setValue(rule.minimum_confidence)
            minimum = self._spin(0, 100)
            minimum.setValue(rule.minimum_objects)
            maximum = self._spin(0, 100)
            maximum.setValue(rule.maximum_objects)
            self.class_rules.setItem(row, 1, label_item)
            self.class_rules.setCellWidget(row, 2, confidence)
            self.class_rules.setCellWidget(row, 3, minimum)
            self.class_rules.setCellWidget(row, 4, maximum)
        self.class_rules.resizeColumnsToContents()

    def _build_class_rules(self) -> tuple[InspectionClassRule, ...]:
        rules = []
        for row in range(self.class_rules.rowCount()):
            enabled = self.class_rules.cellWidget(row, 0)
            confidence = self.class_rules.cellWidget(row, 2)
            minimum = self.class_rules.cellWidget(row, 3)
            maximum = self.class_rules.cellWidget(row, 4)
            if (
                not isinstance(enabled, QCheckBox)
                or not isinstance(confidence, QDoubleSpinBox)
                or not isinstance(minimum, QSpinBox)
                or not isinstance(maximum, QSpinBox)
            ):
                continue
            rules.append(
                InspectionClassRule(
                    self.class_rules.item(row, 1).text().strip(),
                    confidence.value(),
                    minimum.value(),
                    maximum.value(),
                    enabled.isChecked(),
                )
            )
        return tuple(rules)

    @staticmethod
    def _spin(low: int, high: int) -> QSpinBox:
        value = QSpinBox()
        value.setRange(low, high)
        return value

    @staticmethod
    def _double(low: float, high: float) -> QDoubleSpinBox:
        value = QDoubleSpinBox()
        value.setRange(low, high)
        value.setDecimals(2)
        return value
