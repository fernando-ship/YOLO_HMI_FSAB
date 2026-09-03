from dataclasses import replace
from pathlib import Path

import pytest

from hmi_yolo_311d_fsab.infrastructure.config import load_config
from hmi_yolo_311d_fsab.services.configuration_service import ConfigurationService


def test_runtime_configuration_is_saved_atomically(tmp_path: Path) -> None:
    config = load_config(Path.cwd(), {"HMI_YOLO_INFERENCE_ENGINE": "simulated"})
    service = ConfigurationService(tmp_path / "config" / "runtime.ini")
    updated = replace(config, plc=replace(config.plc, host="192.0.2.10", port=9600))

    service.save(updated)

    contents = (tmp_path / "config" / "runtime.ini").read_text(encoding="utf-8")
    assert "host = 192.0.2.10" in contents
    assert "port = 9600" in contents
    assert "engine = simulated" in contents
    assert "best.pt" in contents
    assert "image_size = 640" in contents
    assert not (tmp_path / "config" / "runtime.tmp").exists()


def test_duplicate_io_tags_are_rejected(tmp_path: Path) -> None:
    config = load_config(Path.cwd(), {})
    duplicate = replace(config.io_points[1], tag=config.io_points[0].tag)
    invalid = replace(config, io_points=(config.io_points[0], duplicate))

    with pytest.raises(ValueError, match="duplicados"):
        ConfigurationService(tmp_path / "runtime.ini").save(invalid)
