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
        self._validate_rules(rules)
        self._rules = rules
        self._accepted = 0
        self._rejected = 0

    @staticmethod
    def _validate_rules(rules: InspectionRules) -> None:
        if not rules.expected_label.strip():
            raise ValueError("La clase esperada no puede estar vacia")
        if not 0.0 <= rules.minimum_confidence <= 1.0:
            raise ValueError("La confianza minima debe estar entre 0 y 1")
        if rules.minimum_objects < 0 or rules.maximum_objects < rules.minimum_objects:
            raise ValueError("El rango de objetos no es valido")
        active = [rule for rule in rules.class_rules if rule.enabled]
        if rules.class_rules and not active:
            raise ValueError("Debe existir al menos una clase requerida")
        if any(
            not rule.label.strip()
            or not 0.0 <= rule.minimum_confidence <= 1.0
            or rule.minimum_objects < 0
            or rule.maximum_objects < rule.minimum_objects
            for rule in active
        ):
            raise ValueError("Una regla de clase no es valida")

    def update_rules(self, rules: InspectionRules) -> None:
        self._validate_rules(rules)
        self._rules = rules

    def inspect(self, inference: InferenceResult) -> InspectionResult:
        return self._evaluate(inference, update_counters=True)

    def evaluate(self, inference: InferenceResult) -> InspectionResult:
        return self._evaluate(inference, update_counters=False)

    def _evaluate(self, inference: InferenceResult, *, update_counters: bool) -> InspectionResult:
        started_at = perf_counter()
        rules = self._active_rules()
        failures: list[str] = []
        counts: list[str] = []
        for rule in rules:
            matching = tuple(
                detection
                for detection in inference.detections
                if detection.label == rule.expected_label
                and detection.confidence >= rule.minimum_confidence
            )
            count = len(matching)
            counts.append(f"{rule.expected_label}: {count}")
            if not rule.minimum_objects <= count <= rule.maximum_objects:
                failures.append(
                    f"{rule.expected_label}: {count} valido(s), esperado "
                    f"{rule.minimum_objects}-{rule.maximum_objects} con confianza "
                    f">= {rule.minimum_confidence:.0%}"
                )
        accepted = not failures
        if accepted:
            if update_counters:
                self._accepted += 1
            status = InspectionStatus.OK
            reason = "Clases validadas: " + ", ".join(counts)
        else:
            if update_counters:
                self._rejected += 1
            status = InspectionStatus.NOK
            reason = "; ".join(failures)
        return InspectionResult(
            frame_sequence=inference.frame_sequence,
            status=status,
            reason=reason,
            inspected_at=datetime.now(timezone.utc),
            elapsed_ms=(perf_counter() - started_at) * 1000,
        )

    def quality_score(self, inference: InferenceResult) -> float:
        scores = []
        for rule in self._active_rules():
            scores.append(
                max(
                    (
                        detection.confidence
                        for detection in inference.detections
                        if detection.label == rule.expected_label
                    ),
                    default=0.0,
                )
            )
        return min(scores, default=0.0)

    def _active_rules(self) -> tuple[InspectionRules, ...]:
        if not self._rules.class_rules:
            return (self._rules,)
        return tuple(
            InspectionRules(
                rule.label,
                rule.minimum_confidence,
                rule.minimum_objects,
                rule.maximum_objects,
            )
            for rule in self._rules.class_rules
            if rule.enabled
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
