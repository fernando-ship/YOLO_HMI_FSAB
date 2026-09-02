import pytest

from hmi_yolo_311d_fsab.domain.camera import CameraNotRunningError, CameraState
from hmi_yolo_311d_fsab.infrastructure.simulated_camera import SimulatedCameraClient
from hmi_yolo_311d_fsab.services.camera_service import CameraService


def test_camera_initial_state_and_disconnected_capture() -> None:
    camera = SimulatedCameraClient(8, 6)
    assert camera.get_state() is CameraState.STOPPED
    with pytest.raises(CameraNotRunningError):
        camera.capture_frame()


def test_camera_generates_deterministic_sized_frames() -> None:
    camera = SimulatedCameraClient(8, 6)
    camera.start()
    first = camera.capture_frame()
    second = camera.capture_frame()

    assert first.sequence == 0
    assert second.sequence == 1
    assert len(first.rgb_data) == 8 * 6 * 3
    assert first.rgb_data != second.rgb_data


def test_camera_service_lifecycle() -> None:
    service = CameraService(SimulatedCameraClient(8, 6))
    assert service.start() is CameraState.RUNNING
    assert service.capture_frame().width == 8
    assert service.stop() is CameraState.STOPPED

