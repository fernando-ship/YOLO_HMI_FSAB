from collections.abc import Callable

from PySide6.QtMultimedia import QMediaDevices

from hmi_yolo_311d_fsab.domain.camera_device import CameraBackend, CameraDevice

CameraNameProvider = Callable[[], tuple[str, ...]]


class WindowsCameraDiscovery:
    def __init__(self, name_provider: CameraNameProvider | None = None) -> None:
        self._name_provider = name_provider or self._video_input_names

    def discover(self) -> tuple[CameraDevice, ...]:
        return tuple(
            CameraDevice(
                identifier=str(index),
                display_name=f"{name} (OpenCV {index})",
                backend=CameraBackend.OPENCV,
            )
            for index, name in enumerate(self._name_provider())
        )

    @staticmethod
    def _video_input_names() -> tuple[str, ...]:
        return tuple(device.description() for device in QMediaDevices.videoInputs())
