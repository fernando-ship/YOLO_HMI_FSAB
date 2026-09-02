import logging
from threading import RLock

from hmi_yolo_311d_fsab.domain.plc import (
    ConnectionState,
    PlcConnectionError,
    PlcNotConnectedError,
    PlcValue,
    PlcVariableNotFoundError,
)


class SimulatedPlcClient:
    def __init__(
        self,
        *,
        simulate_connection_error: bool = False,
        initial_variables: dict[str, PlcValue] | None = None,
    ) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._simulate_connection_error = simulate_connection_error
        self._variables = dict(initial_variables or {"machine_ready": True, "part_count": 0})
        self._lock = RLock()
        self._logger = logging.getLogger(__name__)

    def connect(self) -> None:
        with self._lock:
            self._logger.info("Intentando conectar al PLC simulado")
            self._state = ConnectionState.CONNECTING
            if self._simulate_connection_error:
                self._state = ConnectionState.ERROR
                self._logger.error("Error de conexion simulado")
                raise PlcConnectionError("No fue posible conectar con el PLC simulado")
            self._state = ConnectionState.CONNECTED
            self._logger.info("PLC simulado conectado")

    def disconnect(self) -> None:
        with self._lock:
            self._state = ConnectionState.DISCONNECTED
            self._logger.info("PLC simulado desconectado")

    def get_connection_state(self) -> ConnectionState:
        with self._lock:
            return self._state

    def read_variable(self, name: str) -> PlcValue:
        with self._lock:
            self._ensure_connected()
            try:
                return self._variables[name]
            except KeyError as exc:
                raise PlcVariableNotFoundError(f"Variable PLC inexistente: {name}") from exc

    def write_variable(self, name: str, value: PlcValue) -> None:
        with self._lock:
            self._ensure_connected()
            self._variables[name] = value

    def _ensure_connected(self) -> None:
        if self._state is not ConnectionState.CONNECTED:
            raise PlcNotConnectedError("El PLC no esta conectado")

