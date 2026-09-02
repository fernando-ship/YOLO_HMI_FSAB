import logging

from hmi_yolo_311d_fsab.domain.camera import CameraClient, CameraError, CameraFrame, CameraState


class CameraService:
    def __init__(self, client: CameraClient) -> None:
        self._client = client
        self._logger = logging.getLogger(__name__)

    def start(self) -> CameraState:
        try:
            self._client.start()
        except CameraError:
            raise
        except Exception as exc:
            self._logger.exception("Fallo inesperado al iniciar la camara")
            raise CameraError("No fue posible iniciar la camara") from exc
        return self._client.get_state()

    def stop(self) -> CameraState:
        try:
            self._client.stop()
        except CameraError:
            raise
        except Exception as exc:
            self._logger.exception("Fallo inesperado al detener la camara")
            raise CameraError("No fue posible detener la camara") from exc
        return self._client.get_state()

    def get_state(self) -> CameraState:
        return self._client.get_state()

    def capture_frame(self) -> CameraFrame:
        return self._client.capture_frame()

