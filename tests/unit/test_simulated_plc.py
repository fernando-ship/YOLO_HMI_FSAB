import pytest

from hmi_yolo_311d_fsab.domain.plc import (
    ConnectionState,
    PlcConnectionError,
    PlcNotConnectedError,
    PlcVariableNotFoundError,
)
from hmi_yolo_311d_fsab.infrastructure.simulated_plc import SimulatedPlcClient


def test_initial_state_is_disconnected() -> None:
    client = SimulatedPlcClient()
    assert client.get_connection_state() is ConnectionState.DISCONNECTED


def test_connect_and_disconnect() -> None:
    client = SimulatedPlcClient()
    client.connect()
    assert client.get_connection_state() is ConnectionState.CONNECTED
    client.disconnect()
    assert client.get_connection_state() is ConnectionState.DISCONNECTED


def test_read_and_write_variables() -> None:
    client = SimulatedPlcClient(initial_variables={"counter": 1})
    client.connect()
    assert client.read_variable("counter") == 1
    client.write_variable("counter", 2)
    assert client.read_variable("counter") == 2


@pytest.mark.parametrize("operation", ["read", "write"])
def test_operations_are_rejected_while_disconnected(operation: str) -> None:
    client = SimulatedPlcClient()
    with pytest.raises(PlcNotConnectedError):
        if operation == "read":
            client.read_variable("counter")
        else:
            client.write_variable("counter", 1)


def test_missing_variable_is_rejected() -> None:
    client = SimulatedPlcClient()
    client.connect()
    with pytest.raises(PlcVariableNotFoundError):
        client.read_variable("missing")


def test_connection_error_is_deterministic() -> None:
    client = SimulatedPlcClient(simulate_connection_error=True)
    with pytest.raises(PlcConnectionError):
        client.connect()
    assert client.get_connection_state() is ConnectionState.ERROR
