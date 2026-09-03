from dataclasses import dataclass
from enum import Enum


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class HealthSnapshot:
    component: str
    status: HealthStatus
    message: str
    last_heartbeat: float | None
