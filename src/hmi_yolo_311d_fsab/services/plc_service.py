import logging

from hmi_yolo_311d_fsab.domain.plc import ConnectionState, PlcClient, PlcError, PlcValue


class PlcService:
    def __init__(self, client: PlcClient) -> None:
        self._client = client
        self._started = False
        self._logger = logging.getLogger(__name__)

    @property
    def is_started(self) -> bool:
        return self._started

    def start(self) -> None:
        if not self._started:
            self._started = True
            self._logger.info("Servicio PLC iniciado")

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self._client.disconnect()
        finally:
            self._started = False
            self._logger.info("Servicio PLC detenido")

    def connect(self) -> ConnectionState:
        self._ensure_started()
        try:
            self._client.connect()
        except PlcError:
            raise
        except Exception as exc:
            self._logger.exception("Fallo inesperado del cliente PLC")
            raise PlcError("Se produjo un error inesperado al conectar el PLC") from exc
        return self._client.get_connection_state()

    def disconnect(self) -> ConnectionState:
        self._ensure_started()
        try:
            self._client.disconnect()
        except PlcError:
            raise
        except Exception as exc:
            self._logger.exception("Fallo inesperado al desconectar el PLC")
            raise PlcError("Se produjo un error inesperado al desconectar el PLC") from exc
        return self._client.get_connection_state()

    def get_connection_state(self) -> ConnectionState:
        return self._client.get_connection_state()

    def read_variable(self, name: str) -> PlcValue:
        self._ensure_started()
        return self._client.read_variable(name)

    def write_variable(self, name: str, value: PlcValue) -> None:
        self._ensure_started()
        self._client.write_variable(name, value)

    def _ensure_started(self) -> None:
        if not self._started:
            raise PlcError("El servicio PLC no esta iniciado")
