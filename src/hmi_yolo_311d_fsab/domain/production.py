from dataclasses import dataclass
from enum import Enum

from hmi_yolo_311d_fsab.domain.inspection import InspectionCounters, InspectionResult


class ProductionState(Enum):
    IDLE = "idle"
    WAITING_TRIGGER = "waiting_trigger"
    VALIDATING = "validating"
    INSPECTING = "inspecting"
    WAITING_ACK = "waiting_ack"
    ERROR = "error"


@dataclass(frozen=True)
class ProductionCycleResult:
    sequence: int
    state: ProductionState
    inspection: InspectionResult
    counters: InspectionCounters


class ProductionError(Exception):
    """No fue posible completar un ciclo de produccion controlado."""
