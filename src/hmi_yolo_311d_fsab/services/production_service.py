import logging
from dataclasses import replace
from time import perf_counter

from hmi_yolo_311d_fsab.domain.inference import InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionRules, InspectionStatus
from hmi_yolo_311d_fsab.domain.production import (
    ProductionCycleResult,
    ProductionError,
    ProductionState,
)
from hmi_yolo_311d_fsab.domain.recipe import InspectionRecipe, RecipeError
from hmi_yolo_311d_fsab.services.inspection_service import InspectionService
from hmi_yolo_311d_fsab.services.plc_service import PlcService


class ProductionService:
    REQUIRED_TAGS = (
        "trigger_inspection",
        "inspection_busy",
        "inspection_complete",
        "inspection_ok",
        "inspection_nok",
        "inspection_sequence",
        "quality_percent",
        "result_ack",
    )

    def __init__(
        self,
        plc_service: PlcService,
        inspection_service: InspectionService,
        tags: dict[str, str],
        quality_threshold_percent: float = 85.0,
        cycle_timeout_seconds: float = 3.0,
    ) -> None:
        missing = set(self.REQUIRED_TAGS) - tags.keys()
        if missing:
            raise ValueError(f"Faltan tags de produccion: {', '.join(sorted(missing))}")
        self._plc_service = plc_service
        self._inspection_service = inspection_service
        self._tags = tags
        self._quality_threshold_percent = quality_threshold_percent
        self._cycle_timeout_seconds = cycle_timeout_seconds
        self._state = ProductionState.IDLE
        self._sequence = 0
        self._logger = logging.getLogger(__name__)

    def get_state(self) -> ProductionState:
        return self._state

    def reset(self) -> ProductionState:
        self._state = ProductionState.IDLE
        return self._state

    def arm(self) -> ProductionState:
        self._write("inspection_busy", False)
        self._write("inspection_complete", False)
        self._write("inspection_ok", False)
        self._write("inspection_nok", False)
        self._state = ProductionState.WAITING_TRIGGER
        self._logger.info("Ciclo preparado y esperando disparo")
        return self._state

    def simulate_trigger(self) -> None:
        self._write("trigger_inspection", True)

    def execute_if_triggered(self, inference: InferenceResult) -> ProductionCycleResult:
        if self._state is not ProductionState.WAITING_TRIGGER:
            raise ProductionError("El ciclo no esta preparado para aceptar un nuevo trigger")
        trigger = self._plc_service.read_variable(self._tags["trigger_inspection"])
        if trigger is not True:
            raise ProductionError("No existe un disparo de inspeccion activo")

        started_at = perf_counter()
        self._state = ProductionState.VALIDATING
        self._write("inspection_busy", True)
        self._write("inspection_complete", False)
        try:
            self._state = ProductionState.INSPECTING
            inspection = self._inspection_service.inspect(inference)
            self._sequence += 1
            quality = self._inspection_service.quality_score(inference)
            quality_percent = round(quality * 100, 2)
            accepted = (
                inspection.status is InspectionStatus.OK
                and quality_percent >= self._quality_threshold_percent
            )
            if not accepted and inspection.status is InspectionStatus.OK:
                inspection = replace(
                    inspection,
                    status=InspectionStatus.NOK,
                    reason=(
                        f"Calidad {quality_percent:.2f}% menor al minimo "
                        f"{self._quality_threshold_percent:.2f}%"
                    ),
                )
            if perf_counter() - started_at > self._cycle_timeout_seconds:
                raise ProductionError("La inspeccion excedio el timeout del ciclo")
            self._write("inspection_ok", accepted)
            self._write("inspection_nok", not accepted)
            self._write("inspection_sequence", self._sequence)
            self._write("quality_percent", quality_percent)
            self._write("inspection_busy", False)
            self._write("inspection_complete", True)
            self._state = ProductionState.WAITING_ACK
            self._logger.info("Ciclo %s completado: %s", self._sequence, inspection.status.value)
            return ProductionCycleResult(
                self._sequence,
                self._state,
                inspection,
                self._inspection_service.get_counters(),
            )
        except Exception:
            self._state = ProductionState.ERROR
            self._write("inspection_busy", False)
            self._logger.exception("Error durante el ciclo de produccion")
            raise

    def acknowledge(self) -> ProductionState:
        if self._state is not ProductionState.WAITING_ACK:
            raise ProductionError("No existe un resultado pendiente de reconocimiento")
        self._write("inspection_complete", False)
        self._write("inspection_ok", False)
        self._write("inspection_nok", False)
        self._state = ProductionState.WAITING_TRIGGER
        return self._state

    def result_acknowledged(self) -> bool:
        return self._plc_service.read_variable(self._tags["result_ack"]) is True

    def apply_recipe(self, recipe: InspectionRecipe) -> None:
        if self._state not in {ProductionState.IDLE, ProductionState.WAITING_TRIGGER}:
            raise RecipeError("Espere el ACK antes de cambiar la receta")
        self._inspection_service.update_rules(
            InspectionRules(
                recipe.expected_label,
                recipe.minimum_confidence,
                recipe.minimum_objects,
                recipe.maximum_objects,
                recipe.class_rules,
            )
        )
        self._quality_threshold_percent = recipe.quality_threshold_percent
        self._cycle_timeout_seconds = recipe.cycle_timeout_seconds

    def read_io_values(self) -> dict[str, bool | int | float | str]:
        return {
            logical_name: self._plc_service.read_variable(tag)
            for logical_name, tag in self._tags.items()
        }

    def _write(self, logical_name: str, value: bool | int | float | str) -> None:
        self._plc_service.write_variable(self._tags[logical_name], value)
