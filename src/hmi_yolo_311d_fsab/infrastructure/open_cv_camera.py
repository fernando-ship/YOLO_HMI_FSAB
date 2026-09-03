import importlib
import logging
import sys
from threading import RLock
from typing import Protocol, cast

from hmi_yolo_311d_fsab.domain.camera import (
    CameraError,
    CameraFrame,
    CameraNotRunningError,
    CameraState,
)


class VideoFrame(Protocol):
    @property
    def shape(self) -> tuple[int, ...]: ...

    def tobytes(self) -> bytes: ...


class VideoCapture(Protocol):
    def isOpened(self) -> bool: ...  # noqa: N802

    def set(self, property_id: int, value: float) -> bool: ...

    def read(self) -> tuple[bool, object | None]: ...

    def release(self) -> None: ...


class OpenCvApi(Protocol):
    CAP_ANY: int
    CAP_DSHOW: int
    CAP_PROP_FRAME_WIDTH: int
    CAP_PROP_FRAME_HEIGHT: int
    CAP_PROP_FPS: int
    COLOR_BGR2RGB: int

    def VideoCapture(self, source: int | str, backend: int) -> VideoCapture: ...  # noqa: N802

    def cvtColor(self, frame: object, conversion: int) -> VideoFrame: ...  # noqa: N802


class OpenCvCameraClient:
    def __init__(
        self,
        device: str,
        width: int,
        height: int,
        frames_per_second: int,
        *,
        api: OpenCvApi | None = None,
    ) -> None:
        if not device.strip():
            raise ValueError("El dispositivo de camara no puede estar vacio")
        if width <= 0 or height <= 0 or frames_per_second <= 0:
            raise ValueError("La configuracion de captura debe ser positiva")
        self._device = device.strip()
        self._width = width
        self._height = height
        self._frames_per_second = frames_per_second
        self._api = api
        self._capture: VideoCapture | None = None
        self._state = CameraState.STOPPED
        self._sequence = 0
        self._lock = RLock()
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        with self._lock:
            if self._state is CameraState.RUNNING:
                return
            self._release_capture()
            api = self._load_api()
            backend = api.CAP_DSHOW if sys.platform == "win32" else api.CAP_ANY
            source: int | str = int(self._device) if self._device.isdigit() else self._device
            capture = api.VideoCapture(source, backend)
            if not capture.isOpened():
                capture.release()
                self._state = CameraState.ERROR
                raise CameraError(f"No fue posible abrir la camara OpenCV {self._device}")
            capture.set(api.CAP_PROP_FRAME_WIDTH, float(self._width))
            capture.set(api.CAP_PROP_FRAME_HEIGHT, float(self._height))
            capture.set(api.CAP_PROP_FPS, float(self._frames_per_second))
            self._capture = capture
            self._state = CameraState.RUNNING
            self._logger.info("Camara OpenCV %s iniciada", self._device)

    def stop(self) -> None:
        with self._lock:
            self._release_capture()
            self._state = CameraState.STOPPED
            self._logger.info("Camara OpenCV detenida")

    def get_state(self) -> CameraState:
        with self._lock:
            return self._state

    def capture_frame(self) -> CameraFrame:
        with self._lock:
            if self._state is not CameraState.RUNNING or self._capture is None:
                raise CameraNotRunningError("La camara OpenCV no esta iniciada")
            ok, bgr_frame = self._capture.read()
            if not ok or bgr_frame is None:
                self._state = CameraState.ERROR
                raise CameraError("La camara OpenCV dejo de entregar imagenes")
            try:
                rgb_frame = self._load_api().cvtColor(bgr_frame, self._load_api().COLOR_BGR2RGB)
                height, width = rgb_frame.shape[:2]
                rgb_data = rgb_frame.tobytes()
            except Exception as exc:
                self._state = CameraState.ERROR
                raise CameraError("No fue posible convertir el frame de la camara") from exc
            sequence = self._sequence
            self._sequence += 1
            return CameraFrame(width, height, rgb_data, sequence)

    def _load_api(self) -> OpenCvApi:
        if self._api is not None:
            return self._api
        try:
            module = importlib.import_module("cv2")
        except ModuleNotFoundError as exc:
            self._state = CameraState.ERROR
            raise CameraError(
                "OpenCV no esta instalado; instale el extra 'camera' del proyecto"
            ) from exc
        self._api = cast(OpenCvApi, module)
        return self._api

    def _release_capture(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
