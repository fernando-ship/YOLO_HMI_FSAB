from pathlib import Path

import pytest

from hmi_yolo_311d_fsab.infrastructure.config import (
    ConfigurationError,
    InferenceEngineType,
    PlcMode,
    load_config,
)


def test_development_config_selects_simulator() -> None:
    config = load_config(
        Path.cwd(),
        {
            "HMI_YOLO_CAMERA_BACKEND": "simulated",
            "HMI_YOLO_CAMERA_FALLBACK": "true",
            "HMI_YOLO_INFERENCE_ENGINE": "simulated",
        },
    )
    assert config.plc.mode is PlcMode.SIMULATED
    assert config.plc.port == 44818
    assert config.camera.backend.value == "simulated"
    assert config.camera.fallback_to_simulator
    assert config.inference.engine is InferenceEngineType.SIMULATED
    assert config.inference.image_size == 640


def test_yolo_configuration_can_be_selected_with_environment() -> None:
    config = load_config(
        Path.cwd(),
        {
            "HMI_YOLO_INFERENCE_ENGINE": "yolo",
            "HMI_YOLO_MODEL_PATH": "models/custom.pt",
            "HMI_YOLO_DEVICE": "cpu",
            "HMI_YOLO_IOU_THRESHOLD": "0.55",
            "HMI_YOLO_IMAGE_SIZE": "320",
        },
    )

    assert config.inference.engine is InferenceEngineType.YOLO
    assert config.inference.model_path == Path.cwd() / "models" / "custom.pt"
    assert config.inference.device == "cpu"
    assert config.inference.iou_threshold == 0.55
    assert config.inference.image_size == 320


def test_environment_overrides_are_validated() -> None:
    with pytest.raises(ConfigurationError, match="puerto"):
        load_config(Path.cwd(), {"HMI_YOLO_PLC_PORT": "70000"})
