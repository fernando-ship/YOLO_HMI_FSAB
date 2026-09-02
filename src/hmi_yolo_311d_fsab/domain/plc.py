from enum import Enum
from typing import Protocol, TypeAlias, runtime_checkable

PlcValue: TypeAlias = bool | int | float | str


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class PlcError(Exception):
    """Error controlado de una operacion de PLC."""


class PlcConnectionError(PlcError):
    """No fue posible establecer o mantener la conexion."""


class PlcNotConnectedError(PlcError):
    """La operacion requiere una conexion activa."""


class PlcVariableNotFoundError(PlcError):
    """La variable solicitada no existe."""


@runtime_checkable
class PlcClient(Protocol):
    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def get_connection_state(self) -> ConnectionState: ...

    def read_variable(self, name: str) -> PlcValue: ...

    def write_variable(self, name: str, value: PlcValue) -> None: ...

