import pytest

from hmi_yolo_311d_fsab.domain.camera import CameraError, CameraState
from hmi_yolo_311d_fsab.infrastructure.open_cv_camera import OpenCvCameraClient


class FakeFrame:
    shape = (2, 3, 3)

    def tobytes(self) -> bytes:
        return bytes(range(18))


class FakeCapture:
    def __init__(self, *, opened: bool = True) -> None:
        self.opened = opened
        self.released = False
        self.properties: list[tuple[int, float]] = []

    def isOpened(self) -> bool:  # noqa: N802
        return self.opened

    def set(self, property_id: int, value: float) -> bool:
        self.properties.append((property_id, value))
        return True

    def read(self) -> tuple[bool, object | None]:
        return True, object()

    def release(self) -> None:
        self.released = True


class FakeOpenCv:
    CAP_ANY = 0
    CAP_DSHOW = 700
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5
    COLOR_BGR2RGB = 6

    def __init__(self, capture: FakeCapture) -> None:
        self.capture = capture
        self.opened_source: int | str | None = None

    def VideoCapture(self, source: int | str, backend: int) -> FakeCapture:  # noqa: N802
        self.opened_source = source
        return self.capture

    def cvtColor(self, frame: object, conversion: int) -> FakeFrame:  # noqa: N802
        return FakeFrame()


def test_opencv_camera_captures_rgb_frame() -> None:
    capture = FakeCapture()
    api = FakeOpenCv(capture)
    camera = OpenCvCameraClient("0", 640, 480, 10, api=api)

    camera.start()
    frame = camera.capture_frame()

    assert camera.get_state() is CameraState.RUNNING
    assert api.opened_source == 0
    assert (api.CAP_PROP_FRAME_WIDTH, 640.0) in capture.properties
    assert frame.width == 3
    assert frame.height == 2
    assert frame.rgb_data == bytes(range(18))
    assert frame.sequence == 0

    camera.stop()
    assert camera.get_state() is CameraState.STOPPED
    assert capture.released


def test_opencv_camera_reports_open_failure() -> None:
    camera = OpenCvCameraClient("0", 640, 480, 10, api=FakeOpenCv(FakeCapture(opened=False)))

    with pytest.raises(CameraError, match="abrir"):
        camera.start()

    assert camera.get_state() is CameraState.ERROR
