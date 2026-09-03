import logging
from dataclasses import dataclass

from hmi_yolo_311d_fsab.domain.camera import CameraFrame, CameraState
from hmi_yolo_311d_fsab.domain.inference import InferenceResult, InferenceState
from hmi_yolo_311d_fsab.domain.inspection import (
    InspectionCounters,
    InspectionInterlockError,
    InspectionResult,
    InspectionResultStore,
)
from hmi_yolo_311d_fsab.domain.plc import ConnectionState
from hmi_yolo_311d_fsab.domain.production import ProductionCycleResult, ProductionState
from hmi_yolo_311d_fsab.services.camera_service import CameraService
from hmi_yolo_311d_fsab.services.inference_service import InferenceService
from hmi_yolo_311d_fsab.services.inspection_service import InspectionService
from hmi_yolo_311d_fsab.services.plc_service import PlcService
from hmi_yolo_311d_fsab.services.production_service import ProductionService


@dataclass(frozen=True)
class HmiState:
    plc_state: ConnectionState
    camera_state: CameraState
    inference_state: InferenceState
    production_state: ProductionState
    message: str
    simulated_plc: bool
    camera_backend: str = "simulated"


class HmiService:
    def __init__(
        self,
        plc_service: PlcService,
        camera_service: CameraService,
        inference_service: InferenceService,
        inspection_service: InspectionService,
        production_service: ProductionService,
        inspection_store: InspectionResultStore,
        *,
        simulated_plc: bool,
        inference_enabled: bool,
        camera_backend: str = "simulated",
    ) -> None:
        self._plc_service = plc_service
        self._camera_service = camera_service
        self._inference_service = inference_service
        self._inspection_service = inspection_service
        self._production_service = production_service
        self._inspection_store = inspection_store
        self._inference_enabled = inference_enabled
        self._simulated_plc = simulated_plc
        self._camera_backend = camera_backend
        self._started = False
        self._message = "Aplicacion lista"
        self._logger = logging.getLogger(__name__)

    @property
    def is_started(self) -> bool:
        return self._started

    def start(self) -> None:
        if not self._started:
            self._plc_service.start()
            self._started = True
            self._logger.info("Servicio HMI iniciado")

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self._camera_service.stop()
            self._inference_service.stop()
            self._plc_service.stop()
        finally:
            self._started = False
            self._logger.info("Servicio HMI detenido")

    def connect_plc(self) -> HmiState:
        state = self._plc_service.connect()
        self._production_service.arm()
        self._message = "PLC simulado conectado correctamente"
        return self._build_state(state)

    def disconnect_plc(self) -> HmiState:
        state = self._plc_service.disconnect()
        self._production_service.reset()
        self._message = "PLC desconectado"
        return self._build_state(state)

    def get_state(self) -> HmiState:
        return self._build_state(self._plc_service.get_connection_state())

    def start_camera(self) -> HmiState:
        self._camera_service.start()
        if self._inference_enabled:
            self._inference_service.start()
        self._message = f"Camara {self._camera_backend.upper()} iniciada"
        return self.get_state()

    def stop_camera(self) -> HmiState:
        self._camera_service.stop()
        self._inference_service.stop()
        self._message = f"Camara {self._camera_backend.upper()} detenida"
        return self.get_state()

    def capture_frame(self) -> CameraFrame:
        return self._camera_service.capture_frame()

    def process_frame(self, frame: CameraFrame) -> InferenceResult:
        if not self._inference_enabled:
            return InferenceResult(frame.sequence, (), 0.0)
        return self._inference_service.process(frame)

    def inspect(self, inference: InferenceResult) -> tuple[InspectionResult, InspectionCounters]:
        self._require_plc_connection()
        result = self._inspection_service.inspect(inference)
        self._save_inspection(result, source="manual")
        return result, self._inspection_service.get_counters()

    def reset_inspection_counters(self) -> InspectionCounters:
        return self._inspection_service.reset_counters()

    def run_simulated_cycle(
        self, inference: InferenceResult
    ) -> tuple[ProductionCycleResult, dict[str, bool | int | float | str]]:
        self._require_plc_connection()
        self._production_service.simulate_trigger()
        cycle = self._production_service.execute_if_triggered(inference)
        self._save_inspection(cycle.inspection, source="plc")
        return cycle, self._production_service.read_io_values()

    def _require_plc_connection(self) -> None:
        if self._plc_service.get_connection_state() is not ConnectionState.CONNECTED:
            raise InspectionInterlockError(
                "Inspeccion bloqueada: conecte el PLC antes de inspeccionar"
            )

    def _save_inspection(self, result: InspectionResult, *, source: str) -> None:
        try:
            self._inspection_store.save(result, source=source)
        except OSError:
            self._logger.exception("No fue posible guardar el resultado local")

    def acknowledge_cycle(self) -> tuple[ProductionState, dict[str, bool | int | float | str]]:
        state = self._production_service.acknowledge()
        return state, self._production_service.read_io_values()

    def read_plc_snapshot(self) -> dict[str, bool | int | float | str]:
        self._require_plc_connection()
        return self._production_service.read_io_values()

    def _build_state(self, plc_state: ConnectionState) -> HmiState:
        return HmiState(
            plc_state,
            self._camera_service.get_state(),
            self._inference_service.get_state(),
            self._production_service.get_state(),
            self._message,
            self._simulated_plc,
            self._camera_backend,
        )

