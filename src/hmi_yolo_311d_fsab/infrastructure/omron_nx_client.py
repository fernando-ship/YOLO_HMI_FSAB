import importlib
from typing import Any

from hmi_yolo_311d_fsab.domain.plc import (
    ConnectionState,
    PlcConnectionError,
    PlcNotConnectedError,
    PlcValue,
    PlcVariableNotFoundError,
)


class OmronNxEtherNetIpClient:
    """Adaptador de mensajes explicitos para controladores Omron NX/NJ."""

    STANDARD_EXPLICIT_PORT = 44818

    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds
        self._connection: Any = None
        self._state = ConnectionState.DISCONNECTED

    def connect(self) -> None:
        self._state = ConnectionState.CONNECTING
        if self._port != self.STANDARD_EXPLICIT_PORT:
            self._state = ConnectionState.ERROR
            raise PlcConnectionError(
                "Omron EtherNet/IP explicito requiere normalmente el puerto TCP 44818"
            )
        try:
            omron = importlib.import_module("aphyt.omron")
            connection = omron.NSeries()
            connection.connect_explicit(self._host)
            connection.register_session()
            self._connection = connection
            self._state = ConnectionState.CONNECTED
        except ModuleNotFoundError as exc:
            self._state = ConnectionState.ERROR
            raise PlcConnectionError(
                "Falta APHYT; instale el extra del PLC con pip install -e .[plc]"
            ) from exc
        except Exception as exc:
            self._state = ConnectionState.ERROR
            raise PlcConnectionError(
                f"No fue posible conectar con el Omron NX en {self._host}: {exc}"
            ) from exc

    def disconnect(self) -> None:
        connection = self._connection
        self._connection = None
        try:
            if connection is not None:
                connection.unregister_session()
                connection.close_explicit()
        finally:
            self._state = ConnectionState.DISCONNECTED

    def get_connection_state(self) -> ConnectionState:
        return self._state

    def read_variable(self, name: str) -> PlcValue:
        connection = self._require_connection()
        try:
            value: PlcValue = connection.read_variable(name)
            return value
        except Exception as exc:
            self._state = ConnectionState.ERROR
            raise PlcVariableNotFoundError(f"No se pudo leer el tag '{name}': {exc}") from exc

    def write_variable(self, name: str, value: PlcValue) -> None:
        connection = self._require_connection()
        try:
            connection.write_variable(name, value)
        except Exception as exc:
            self._state = ConnectionState.ERROR
            raise PlcVariableNotFoundError(f"No se pudo escribir el tag '{name}': {exc}") from exc

    def _require_connection(self) -> Any:
        if self._connection is None or self._state is not ConnectionState.CONNECTED:
            raise PlcNotConnectedError("El PLC Omron NX no esta conectado")
        return self._connection
