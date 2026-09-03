import logging
from threading import RLock

from hmi_yolo_311d_fsab.domain.camera import (
    CameraFrame,
    CameraNotRunningError,
    CameraState,
)


class SimulatedCameraClient:
    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Las dimensiones de la camara deben ser positivas")
        self._width = width
        self._height = height
        self._state = CameraState.STOPPED
        self._sequence = 0
        self._lock = RLock()
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        with self._lock:
            self._state = CameraState.RUNNING
            self._logger.info("Camara simulada iniciada")

    def stop(self) -> None:
        with self._lock:
            self._state = CameraState.STOPPED
            self._logger.info("Camara simulada detenida")

    def get_state(self) -> CameraState:
        with self._lock:
            return self._state

    def capture_frame(self) -> CameraFrame:
        with self._lock:
            if self._state is not CameraState.RUNNING:
                raise CameraNotRunningError("La camara simulada no esta iniciada")
            sequence = self._sequence
            self._sequence += 1
            return CameraFrame(
                width=self._width,
                height=self._height,
                rgb_data=self._generate_rgb_data(sequence),
                sequence=sequence,
            )

    def _generate_rgb_data(self, sequence: int) -> bytes:
        data = bytearray(self._width * self._height * 3)
        offset = 0
        for y in range(self._height):
            for x in range(self._width):
                data[offset] = (x + sequence * 4) % 256
                data[offset + 1] = (y * 2 + sequence * 3) % 256
                data[offset + 2] = (x + y + sequence * 7) % 256
                offset += 3
        return bytes(data)
