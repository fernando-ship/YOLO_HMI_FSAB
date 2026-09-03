from typing import Protocol

from hmi_yolo_311d_fsab.domain.camera_device import CameraDevice


class CameraDiscovery(Protocol):
    def discover(self) -> tuple[CameraDevice, ...]: ...


class CameraDiscoveryService:
    def __init__(self, discovery: CameraDiscovery) -> None:
        self._discovery = discovery

    def discover(self) -> tuple[CameraDevice, ...]:
        return self._discovery.discover()
