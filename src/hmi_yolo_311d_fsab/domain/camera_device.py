from dataclasses import dataclass
from enum import Enum


class CameraBackend(Enum):
    SIMULATED = "simulated"
    OPENCV = "opencv"
    V4L2 = "v4l2"
    ARGUS = "argus"


class CaptureProfile(Enum):
    MAX_QUALITY = "max_quality"
    BALANCED = "balanced"
    MAX_PERFORMANCE = "max_performance"
    MANUAL = "manual"


@dataclass(frozen=True)
class CameraDevice:
    identifier: str
    display_name: str
    backend: CameraBackend

