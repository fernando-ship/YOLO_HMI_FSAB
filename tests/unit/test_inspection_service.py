from hmi_yolo_311d_fsab.domain.inference import (
    BoundingBox,
    Detection,
    InferenceResult,
)
from hmi_yolo_311d_fsab.domain.inspection import (
    InspectionClassRule,
    InspectionRules,
    InspectionStatus,
)
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


def test_multiclass_rules_require_every_enabled_class() -> None:
    rules = InspectionRules(
        "legacy",
        0.5,
        1,
        1,
        (
            InspectionClassRule("Bolsa", 0.70, 1, 1),
            InspectionClassRule("Label", 0.80, 1, 1),
            InspectionClassRule("QR CODE", 0.75, 1, 1),
        ),
    )
    service = InspectionService(rules)
    complete = make_result(
        Detection("Bolsa", 0.95, BoundingBox(0, 0, 10, 10)),
        Detection("Label", 0.82, BoundingBox(0, 0, 10, 10)),
        Detection("QR CODE", 0.90, BoundingBox(0, 0, 10, 10)),
    )
    missing_label = make_result(
        Detection("Bolsa", 0.95, BoundingBox(0, 0, 10, 10)),
        Detection("QR CODE", 0.90, BoundingBox(0, 0, 10, 10)),
    )

    assert service.inspect(complete).status is InspectionStatus.OK
    rejected = service.inspect(missing_label)
    assert rejected.status is InspectionStatus.NOK
    assert "Label" in rejected.reason
    assert service.quality_score(complete) == 0.82
    assert service.quality_score(missing_label) == 0.0
