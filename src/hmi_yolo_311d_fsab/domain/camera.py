from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class CameraState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


@dataclass(frozen=True)
class CameraFrame:
    width: int
    height: int
    rgb_data: bytes
    sequence: int


class CameraError(Exception):
    """Error controlado de una operacion de camara."""


class CameraNotRunningError(CameraError):
    """La captura requiere que la camara este iniciada."""


@runtime_checkable
class CameraClient(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def get_state(self) -> CameraState: ...

    def capture_frame(self) -> CameraFrame: ...

