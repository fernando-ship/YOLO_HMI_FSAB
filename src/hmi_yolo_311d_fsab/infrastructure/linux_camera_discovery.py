from pathlib import Path

from hmi_yolo_311d_fsab.domain.camera_device import CameraBackend, CameraDevice


class LinuxCameraDiscovery:
    def __init__(self, device_root: Path = Path("/dev")) -> None:
        self._device_root = device_root

    def discover(self) -> tuple[CameraDevice, ...]:
        devices = []
        for path in sorted(self._device_root.glob("video*")):
            if path.name.removeprefix("video").isdigit():
                devices.append(
                    CameraDevice(
                        identifier=str(path),
                        display_name=f"Camara V4L2 ({path.name})",
                        backend=CameraBackend.V4L2,
                    )
                )
        return tuple(devices)
