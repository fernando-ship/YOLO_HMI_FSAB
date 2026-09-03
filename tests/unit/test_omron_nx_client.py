import pytest

from hmi_yolo_311d_fsab.domain.plc import ConnectionState, PlcConnectionError
from hmi_yolo_311d_fsab.infrastructure.omron_nx_client import OmronNxEtherNetIpClient


def test_rejects_nonstandard_explicit_message_port() -> None:
    client = OmronNxEtherNetIpClient("192.168.250.1", 1234, 2.0)

    with pytest.raises(PlcConnectionError, match="44818"):
        client.connect()

    assert client.get_connection_state() is ConnectionState.ERROR
