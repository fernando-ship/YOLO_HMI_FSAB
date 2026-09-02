from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AlarmSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlarmState(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class Alarm:
    identifier: int
    source: str
    message: str
    severity: AlarmSeverity
    state: AlarmState
    created_at: datetime

