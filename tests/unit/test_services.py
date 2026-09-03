import pytest

from hmi_yolo_311d_fsab.domain.inspection import InspectionInterlockError, InspectionRules
from hmi_yolo_311d_fsab.domain.plc import ConnectionState, PlcError
from hmi_yolo_311d_fsab.infrastructure.simulated_camera import SimulatedCameraClient
from hmi_yolo_311d_fsab.infrastructure.simulated_inference import SimulatedInferenceEngine
from hmi_yolo_311d_fsab.infrastructure.simulated_plc import SimulatedPlcClient
from hmi_yolo_311d_fsab.services.camera_service import CameraService
from hmi_yolo_311d_fsab.services.hmi_service import HmiService
from hmi_yolo_311d_fsab.services.inference_service import InferenceService
from hmi_yolo_311d_fsab.services.inspection_service import InspectionService
from hmi_yolo_311d_fsab.services.plc_service import PlcService
from hmi_yolo_311d_fsab.services.production_service import ProductionService


class MemoryInspectionStore:
    def __init__(self) -> None:
        self.saved: list[tuple[object, str]] = []

    def save(self, result: object, *, source: str) -> None:
        self.saved.append((result, source))

    def purge_expired(self) -> int:
        return 0

    def load(self) -> tuple[object, ...]:
        return ()

    def clear(self) -> int:
        return 0

    def storage_bytes(self) -> int:
        return 0


def test_plc_service_lifecycle() -> None:
    service = PlcService(SimulatedPlcClient())
    with pytest.raises(PlcError):
        service.connect()
    service.start()
    assert service.connect() is ConnectionState.CONNECTED
    service.stop()
    assert service.get_connection_state() is ConnectionState.DISCONNECTED
    assert not service.is_started


def test_hmi_service_lifecycle_and_state() -> None:
    plc_service = PlcService(SimulatedPlcClient())
    camera_service = CameraService(SimulatedCameraClient(16, 12))
    inference_service = InferenceService(SimulatedInferenceEngine(), 0.5)
    inspection_service = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    production_service = ProductionService(
        plc_service,
        inspection_service,
        {
            "trigger_inspection": "trigger_inspection",
            "inspection_busy": "inspection_busy",
            "inspection_complete": "inspection_complete",
            "inspection_ok": "inspection_ok",
            "inspection_nok": "inspection_nok",
            "inspection_sequence": "inspection_sequence",
            "quality_percent": "quality_percent",
            "result_ack": "result_ack",
        },
    )
    service = HmiService(
        plc_service,
        camera_service,
        inference_service,
        inspection_service,
        production_service,
        MemoryInspectionStore(),
        simulated_plc=True,
        inference_enabled=True,
    )
    service.start()
    connected = service.connect_plc()
    assert connected.plc_state is ConnectionState.CONNECTED
    assert connected.simulated_plc
    disconnected = service.disconnect_plc()
    assert disconnected.plc_state is ConnectionState.DISCONNECTED
    service.stop()
    assert not service.is_started
    assert not plc_service.is_started


def test_hmi_service_coordinates_camera() -> None:
    plc_service = PlcService(SimulatedPlcClient())
    camera_service = CameraService(SimulatedCameraClient(16, 12))
    inference_service = InferenceService(SimulatedInferenceEngine(), 0.5)
    inspection_service = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    production_service = ProductionService(
        plc_service,
        inspection_service,
        {
            "trigger_inspection": "trigger_inspection",
            "inspection_busy": "inspection_busy",
            "inspection_complete": "inspection_complete",
            "inspection_ok": "inspection_ok",
            "inspection_nok": "inspection_nok",
            "inspection_sequence": "inspection_sequence",
            "quality_percent": "quality_percent",
            "result_ack": "result_ack",
        },
    )
    service = HmiService(
        plc_service,
        camera_service,
        inference_service,
        inspection_service,
        production_service,
        MemoryInspectionStore(),
        simulated_plc=True,
        inference_enabled=True,
    )
    service.start()

    running = service.start_camera()
    frame = service.capture_frame()
    result = service.process_frame(frame)
    stopped = service.stop_camera()

    assert running.camera_state.value == "running"
    assert len(frame.rgb_data) == 16 * 12 * 3
    assert result.detections[0].label == "pieza"
    assert stopped.camera_state.value == "stopped"
    service.stop()


def test_inspection_is_blocked_until_plc_is_connected() -> None:
    plc_service = PlcService(SimulatedPlcClient())
    camera_service = CameraService(SimulatedCameraClient(16, 12))
    inference_service = InferenceService(SimulatedInferenceEngine(), 0.5)
    inspection_service = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    production_service = ProductionService(
        plc_service,
        inspection_service,
        {
            "trigger_inspection": "trigger_inspection",
            "inspection_busy": "inspection_busy",
            "inspection_complete": "inspection_complete",
            "inspection_ok": "inspection_ok",
            "inspection_nok": "inspection_nok",
            "inspection_sequence": "inspection_sequence",
            "quality_percent": "quality_percent",
            "result_ack": "result_ack",
        },
    )
    store = MemoryInspectionStore()
    service = HmiService(
        plc_service,
        camera_service,
        inference_service,
        inspection_service,
        production_service,
        store,
        simulated_plc=True,
        inference_enabled=True,
    )
    service.start()
    service.start_camera()
    inference = service.process_frame(service.capture_frame())

    with pytest.raises(InspectionInterlockError, match="conecte el PLC"):
        service.inspect(inference)
    assert store.saved == []

    service.connect_plc()
    service.inspect(inference)
    assert store.saved[0][1] == "manual"
    service.stop()
