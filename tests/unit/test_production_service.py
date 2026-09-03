import pytest

from hmi_yolo_311d_fsab.domain.inference import BoundingBox, Detection, InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import InspectionRules, InspectionStatus
from hmi_yolo_311d_fsab.domain.production import ProductionError, ProductionState
from hmi_yolo_311d_fsab.infrastructure.simulated_plc import SimulatedPlcClient
from hmi_yolo_311d_fsab.services.inspection_service import InspectionService
from hmi_yolo_311d_fsab.services.plc_service import PlcService
from hmi_yolo_311d_fsab.services.production_service import ProductionService

TAGS = {
    "trigger_inspection": "trigger",
    "inspection_busy": "busy",
    "inspection_complete": "complete",
    "inspection_ok": "ok",
    "inspection_nok": "nok",
    "inspection_sequence": "sequence",
    "quality_percent": "quality",
    "result_ack": "ack",
}


def build_service() -> tuple[ProductionService, SimulatedPlcClient]:
    client = SimulatedPlcClient(initial_variables={tag: False for tag in TAGS.values()})
    plc = PlcService(client)
    plc.start()
    client.connect()
    inspection = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    return ProductionService(plc, inspection, TAGS), client


def test_cycle_requires_trigger() -> None:
    service, _ = build_service()
    service.arm()
    with pytest.raises(ProductionError, match="disparo"):
        service.execute_if_triggered(InferenceResult(0, (), 1.0))


def test_complete_ok_handshake_and_acknowledge() -> None:
    service, client = build_service()
    service.arm()
    service.simulate_trigger()
    detection = Detection("pieza", 0.92, BoundingBox(0, 0, 10, 10))
    cycle = service.execute_if_triggered(InferenceResult(4, (detection,), 2.0))

    assert cycle.state is ProductionState.WAITING_ACK
    assert cycle.inspection.status is InspectionStatus.OK
    assert client.read_variable("busy") is False
    assert client.read_variable("complete") is True
    assert client.read_variable("ok") is True
    assert client.read_variable("sequence") == 1
    assert client.read_variable("quality") == 92.0

    assert service.acknowledge() is ProductionState.WAITING_TRIGGER
    assert client.read_variable("complete") is False
    assert client.read_variable("ok") is False


def test_nok_sets_exclusive_output() -> None:
    service, client = build_service()
    service.arm()
    service.simulate_trigger()
    cycle = service.execute_if_triggered(InferenceResult(5, (), 2.0))

    assert cycle.inspection.status is InspectionStatus.NOK
    assert client.read_variable("ok") is False
    assert client.read_variable("nok") is True


def test_held_trigger_cannot_start_second_cycle_before_ack() -> None:
    service, _ = build_service()
    service.arm()
    service.simulate_trigger()
    service.execute_if_triggered(InferenceResult(1, (), 1.0))

    with pytest.raises(ProductionError, match="no esta preparado"):
        service.execute_if_triggered(InferenceResult(2, (), 1.0))


def test_quality_threshold_can_reject_otherwise_valid_detection() -> None:
    client = SimulatedPlcClient(initial_variables={tag: False for tag in TAGS.values()})
    plc = PlcService(client)
    plc.start()
    client.connect()
    inspection = InspectionService(InspectionRules("pieza", 0.5, 1, 1))
    service = ProductionService(plc, inspection, TAGS, quality_threshold_percent=90.0)
    service.arm()
    service.simulate_trigger()
    detection = Detection("pieza", 0.80, BoundingBox(0, 0, 10, 10))

    cycle = service.execute_if_triggered(InferenceResult(3, (detection,), 1.0))

    assert cycle.inspection.status is InspectionStatus.NOK
    assert client.read_variable("quality") == 80.0
