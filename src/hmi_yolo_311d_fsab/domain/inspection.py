from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol


class InspectionStatus(Enum):
    IDLE = "idle"
    OK = "ok"
    NOK = "nok"
    ERROR = "error"


@dataclass(frozen=True)
class InspectionClassRule:
    label: str
    minimum_confidence: float
    minimum_objects: int
    maximum_objects: int
    enabled: bool = True


@dataclass(frozen=True)
class InspectionRules:
    expected_label: str
    minimum_confidence: float
    minimum_objects: int
    maximum_objects: int
    class_rules: tuple[InspectionClassRule, ...] = ()


@dataclass(frozen=True)
class InspectionResult:
    frame_sequence: int
    status: InspectionStatus
    reason: str
    inspected_at: datetime
    elapsed_ms: float


@dataclass(frozen=True)
class InspectionCounters:
    total: int
    accepted: int
    rejected: int


@dataclass(frozen=True)
class StoredInspection:
    frame_sequence: int
    status: InspectionStatus
    reason: str
    inspected_at: datetime
    elapsed_ms: float
    source: str


class InspectionError(Exception):
    """No fue posible completar una inspeccion controlada."""


class InspectionInterlockError(InspectionError):
    """La inspeccion esta bloqueada por una condicion de seguridad."""


class InspectionResultStore(Protocol):
    def save(self, result: InspectionResult, *, source: str) -> None: ...

    def purge_expired(self) -> int: ...

    def load(self) -> tuple[StoredInspection, ...]: ...

    def clear(self) -> int: ...

    def storage_bytes(self) -> int: ...
