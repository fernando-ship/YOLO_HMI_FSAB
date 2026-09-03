from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from hmi_yolo_311d_fsab.domain.camera import CameraFrame


class InferenceState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: BoundingBox


@dataclass(frozen=True)
class InferenceResult:
    frame_sequence: int
    detections: tuple[Detection, ...]
    elapsed_ms: float


class InferenceError(Exception):
    """Error controlado durante la inferencia."""


class InferenceNotRunningError(InferenceError):
    """El motor debe estar iniciado antes de procesar frames."""


@runtime_checkable
class InferenceEngine(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def get_state(self) -> InferenceState: ...

    def infer(self, frame: CameraFrame, confidence_threshold: float) -> InferenceResult: ...
