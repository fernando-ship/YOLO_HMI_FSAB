from dataclasses import dataclass
from enum import Enum

from hmi_yolo_311d_fsab.domain.plc import PlcValue


class IoDirection(Enum):
    INPUT = "input"
    OUTPUT = "output"


class IoDataType(Enum):
    BOOLEAN = "bool"
    INTEGER = "int"
    FLOAT = "float"
    TEXT = "str"


@dataclass(frozen=True)
class IoPoint:
    logical_name: str
    tag: str
    data_type: IoDataType
    direction: IoDirection
    writable: bool
    value: PlcValue

