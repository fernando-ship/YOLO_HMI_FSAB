import logging

from hmi_yolo_311d_fsab.domain.inference import InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionStatus
from hmi_yolo_311d_fsab.domain.production import (
    ProductionCycleResult,
    ProductionError,
    ProductionState,
)
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
    )

    def __init__(
        self,
        plc_service: PlcService,
        inspection_service: InspectionService,
        tags: dict[str, str],
    ) -> None:
        missing = set(self.REQUIRED_TAGS) - tags.keys()
        if missing:
            raise ValueError(f"Faltan tags de produccion: {', '.join(sorted(missing))}")
        self._plc_service = plc_service
        self._inspection_service = inspection_service
        self._tags = tags
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
        if self._state is ProductionState.INSPECTING:
            raise ProductionError("Ya existe una inspeccion en curso")
        trigger = self._plc_service.read_variable(self._tags["trigger_inspection"])
        if trigger is not True:
            raise ProductionError("No existe un disparo de inspeccion activo")

        self._state = ProductionState.INSPECTING
        self._write("inspection_busy", True)
        self._write("inspection_complete", False)
        try:
            inspection = self._inspection_service.inspect(inference)
            self._sequence += 1
            accepted = inspection.status is InspectionStatus.OK
            self._write("inspection_ok", accepted)
            self._write("inspection_nok", not accepted)
            self._write("inspection_sequence", self._sequence)
            quality = max((detection.confidence for detection in inference.detections), default=0.0)
            self._write("quality_percent", round(quality * 100, 2))
            self._write("trigger_inspection", False)
            self._write("inspection_busy", False)
            self._write("inspection_complete", True)
            self._state = ProductionState.COMPLETED
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
        self._write("inspection_complete", False)
        self._write("inspection_ok", False)
        self._write("inspection_nok", False)
        self._state = ProductionState.WAITING_TRIGGER
        return self._state

    def read_io_values(self) -> dict[str, bool | int | float | str]:
        return {
            logical_name: self._plc_service.read_variable(tag)
            for logical_name, tag in self._tags.items()
        }

    def _write(self, logical_name: str, value: bool | int | float | str) -> None:
        self._plc_service.write_variable(self._tags[logical_name], value)

