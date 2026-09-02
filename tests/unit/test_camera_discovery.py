from pathlib import Path

from hmi_yolo_311d_fsab.domain.camera_device import CameraBackend
from hmi_yolo_311d_fsab.infrastructure.linux_camera_discovery import LinuxCameraDiscovery
from hmi_yolo_311d_fsab.services.camera_discovery_service import CameraDiscoveryService


def test_discovers_only_numbered_video_nodes(tmp_path: Path) -> None:
    (tmp_path / "video0").touch()
    (tmp_path / "video2").touch()
    (tmp_path / "video-invalid").touch()
    (tmp_path / "media0").touch()

    devices = CameraDiscoveryService(LinuxCameraDiscovery(tmp_path)).discover()

    assert [device.identifier for device in devices] == [
        str(tmp_path / "video0"),
        str(tmp_path / "video2"),
    ]
    assert all(device.backend is CameraBackend.V4L2 for device in devices)


def test_no_camera_returns_empty_result(tmp_path: Path) -> None:
    assert LinuxCameraDiscovery(tmp_path).discover() == ()

