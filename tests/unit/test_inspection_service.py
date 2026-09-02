from hmi_yolo_311d_fsab.domain.inference import (
    BoundingBox,
    Detection,
    InferenceResult,
)
from hmi_yolo_311d_fsab.domain.inspection import InspectionRules, InspectionStatus
from hmi_yolo_311d_fsab.services.inspection_service import InspectionService


def make_result(*detections: Detection) -> InferenceResult:
    return InferenceResult(10, detections, 2.0)


def test_matching_detection_is_ok() -> None:
    service = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    detection = Detection("pieza", 0.92, BoundingBox(0, 0, 10, 10))
    result = service.inspect(make_result(detection))

    assert result.status is InspectionStatus.OK
    assert service.get_counters().accepted == 1


def test_missing_detection_is_nok() -> None:
    service = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    result = service.inspect(make_result())

    assert result.status is InspectionStatus.NOK
    assert service.get_counters().rejected == 1


def test_wrong_class_or_low_confidence_is_nok() -> None:
    service = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    wrong_class = Detection("defecto", 0.99, BoundingBox(0, 0, 10, 10))
    low_confidence = Detection("pieza", 0.70, BoundingBox(0, 0, 10, 10))

    assert service.inspect(make_result(wrong_class)).status is InspectionStatus.NOK
    assert service.inspect(make_result(low_confidence)).status is InspectionStatus.NOK


def test_counters_can_be_reset() -> None:
    service = InspectionService(InspectionRules("pieza", 0.85, 1, 1))
    service.inspect(make_result())
    counters = service.reset_counters()

    assert counters.total == 0
    assert counters.accepted == 0
    assert counters.rejected == 0

