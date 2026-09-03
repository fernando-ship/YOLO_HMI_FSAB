from pathlib import Path

import pytest

from hmi_yolo_311d_fsab.infrastructure.config import (
    ConfigurationError,
    PlcMode,
    load_config,
)


def test_development_config_selects_simulator() -> None:
    config = load_config(
        Path.cwd(),
        {
            "HMI_YOLO_CAMERA_BACKEND": "simulated",
            "HMI_YOLO_CAMERA_FALLBACK": "true",
        },
    )
    assert config.plc.mode is PlcMode.SIMULATED
    assert config.plc.port == 44818
    assert config.camera.backend.value == "simulated"
    assert config.camera.fallback_to_simulator


def test_environment_overrides_are_validated() -> None:
    with pytest.raises(ConfigurationError, match="puerto"):
        load_config(Path.cwd(), {"HMI_YOLO_PLC_PORT": "70000"})

