import configparser
import os
from pathlib import Path

from hmi_yolo_311d_fsab.infrastructure.config import AppConfig


class ConfigurationService:
    def __init__(self, runtime_file: Path) -> None:
        self._runtime_file = runtime_file

    def save(self, config: AppConfig) -> None:
        self._validate(config)
        project_root = self._runtime_file.parent.parent
        parser = configparser.ConfigParser()
        parser["application"] = {
            "log_level": config.log_level,
            "config_dir": self._portable_path(config.paths.config_dir, project_root),
            "log_dir": self._portable_path(config.paths.log_dir, project_root),
            "data_dir": self._portable_path(config.paths.data_dir, project_root),
        }
        parser["appearance"] = {
            "theme": config.appearance.theme,
            "reduced_motion": str(config.appearance.reduced_motion).lower(),
        }
        parser["plc"] = {
            "mode": config.plc.mode.value,
            "host": config.plc.host,
            "port": str(config.plc.port),
            "timeout_seconds": str(config.plc.timeout_seconds),
            "reconnect_interval_seconds": str(config.plc.reconnect_interval_seconds),
            "simulate_connection_error": str(config.plc.simulate_connection_error).lower(),
        }
        parser["camera"] = {
            "backend": config.camera.backend.value,
            "device": config.camera.device,
            "sensor_id": str(config.camera.sensor_id),
            "profile": config.camera.profile.value,
            "width": str(config.camera.width),
            "height": str(config.camera.height),
            "frames_per_second": str(config.camera.frames_per_second),
            "pixel_format": config.camera.pixel_format,
            "timeout_seconds": str(config.camera.timeout_seconds),
            "reconnect_interval_seconds": str(config.camera.reconnect_interval_seconds),
            "buffer_count": str(config.camera.buffer_count),
            "rotation_degrees": str(config.camera.rotation_degrees),
            "horizontal_flip": str(config.camera.horizontal_flip).lower(),
            "vertical_flip": str(config.camera.vertical_flip).lower(),
            "fallback_to_simulator": str(config.camera.fallback_to_simulator).lower(),
        }
        parser["inference"] = {
            "enabled": str(config.inference.enabled).lower(),
            "confidence_threshold": str(config.inference.confidence_threshold),
            "engine": config.inference.engine.value,
            "model_path": self._portable_path(config.inference.model_path, project_root),
            "device": config.inference.device,
            "iou_threshold": str(config.inference.iou_threshold),
            "image_size": str(config.inference.image_size),
        }
        parser["inspection"] = {
            "expected_label": config.inspection.expected_label,
            "minimum_confidence": str(config.inspection.minimum_confidence),
            "minimum_objects": str(config.inspection.minimum_objects),
            "maximum_objects": str(config.inspection.maximum_objects),
        }
        parser["production"] = {
            "quality_threshold_percent": str(config.production.quality_threshold_percent),
            "cycle_timeout_seconds": str(config.production.cycle_timeout_seconds),
            "maximum_frame_age_ms": str(config.production.maximum_frame_age_ms),
            "plc_poll_interval_ms": str(config.production.plc_poll_interval_ms),
        }
        for point in config.io_points:
            parser[f"io.{point.logical_name}"] = {
                "tag": point.tag,
                "data_type": point.data_type.value,
                "direction": point.direction.value,
                "writable": str(point.writable).lower(),
            }
        self._runtime_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._runtime_file.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            parser.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self._runtime_file)

    @staticmethod
    def _validate(config: AppConfig) -> None:
        if not config.plc.host:
            raise ValueError("La direccion del PLC no puede estar vacia")
        if not config.inspection.expected_label:
            raise ValueError("La clase esperada no puede estar vacia")
        if not config.camera.device.strip():
            raise ValueError("El puerto o dispositivo de camara no puede estar vacio")
        if config.inspection.maximum_objects < config.inspection.minimum_objects:
            raise ValueError("El rango de objetos no es valido")
        if not 0 <= config.production.quality_threshold_percent <= 100:
            raise ValueError("El porcentaje de calidad debe estar entre 0 y 100")
        if config.production.cycle_timeout_seconds <= 0:
            raise ValueError("El timeout del ciclo debe ser positivo")
        if config.production.maximum_frame_age_ms <= 0:
            raise ValueError("La antiguedad maxima del frame debe ser positiva")
        if config.production.plc_poll_interval_ms < 50:
            raise ValueError("El sondeo del PLC debe ser de al menos 50 ms")
        if any(not point.tag.strip() for point in config.io_points):
            raise ValueError("Todos los puntos de E/S necesitan un tag")
        tags = [point.tag for point in config.io_points]
        if len(tags) != len(set(tags)):
            raise ValueError("Los tags de E/S no pueden estar duplicados")
        if not 0.0 <= config.inference.iou_threshold <= 1.0:
            raise ValueError("El umbral IoU debe estar entre 0 y 1")
        if not 32 <= config.inference.image_size <= 4096:
            raise ValueError("El tamano de imagen YOLO debe estar entre 32 y 4096")

    @staticmethod
    def _portable_path(path: Path, project_root: Path) -> str:
        try:
            return str(path.relative_to(project_root))
        except ValueError:
            return str(path)
