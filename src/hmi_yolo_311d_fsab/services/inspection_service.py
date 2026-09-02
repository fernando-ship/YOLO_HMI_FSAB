from datetime import datetime, timezone
from time import perf_counter

from hmi_yolo_311d_fsab.domain.inference import InferenceResult
from hmi_yolo_311d_fsab.domain.inspection import (
    InspectionCounters,
    InspectionResult,
    InspectionRules,
    InspectionStatus,
)


class InspectionService:
    def __init__(self, rules: InspectionRules) -> None:
        if not rules.expected_label.strip():
            raise ValueError("La clase esperada no puede estar vacia")
        if not 0.0 <= rules.minimum_confidence <= 1.0:
            raise ValueError("La confianza minima debe estar entre 0 y 1")
        if rules.minimum_objects < 0 or rules.maximum_objects < rules.minimum_objects:
            raise ValueError("El rango de objetos no es valido")
        self._rules = rules
        self._accepted = 0
        self._rejected = 0

    def inspect(self, inference: InferenceResult) -> InspectionResult:
        started_at = perf_counter()
        matching = tuple(
            detection
            for detection in inference.detections
            if detection.label == self._rules.expected_label
            and detection.confidence >= self._rules.minimum_confidence
        )
        count = len(matching)
        accepted = self._rules.minimum_objects <= count <= self._rules.maximum_objects
        if accepted:
            self._accepted += 1
            status = InspectionStatus.OK
            reason = f"Se encontraron {count} objetos validos"
        else:
            self._rejected += 1
            status = InspectionStatus.NOK
            reason = (
                f"Objetos validos: {count}; esperado: "
                f"{self._rules.minimum_objects}-{self._rules.maximum_objects}"
            )
        return InspectionResult(
            frame_sequence=inference.frame_sequence,
            status=status,
            reason=reason,
            inspected_at=datetime.now(timezone.utc),
            elapsed_ms=(perf_counter() - started_at) * 1000,
        )

    def get_counters(self) -> InspectionCounters:
        return InspectionCounters(
            total=self._accepted + self._rejected,
            accepted=self._accepted,
            rejected=self._rejected,
        )

    def reset_counters(self) -> InspectionCounters:
        self._accepted = 0
        self._rejected = 0
        return self.get_counters()

