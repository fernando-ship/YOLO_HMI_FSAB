import configparser
import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from hmi_yolo_311d_fsab.domain.camera_device import CameraBackend, CaptureProfile
from hmi_yolo_311d_fsab.domain.io_points import IoDataType, IoDirection, IoPoint


class ConfigurationError(ValueError):
    """La configuracion no es valida para iniciar la aplicacion."""


class PlcMode(Enum):
    SIMULATED = "simulated"
    REAL = "real"


@dataclass(frozen=True)
class PlcConfig:
    mode: PlcMode
    host: str
    port: int
    timeout_seconds: float
    reconnect_interval_seconds: float
    simulate_connection_error: bool


@dataclass(frozen=True)
class CameraConfig:
    width: int
    height: int
    frames_per_second: int
    backend: CameraBackend = CameraBackend.SIMULATED
    device: str = "/dev/video0"
    sensor_id: int = 0
    profile: CaptureProfile = CaptureProfile.BALANCED
    pixel_format: str = "AUTO"
    timeout_seconds: float = 3.0
    reconnect_interval_seconds: float = 5.0
    buffer_count: int = 4
    rotation_degrees: int = 0
    horizontal_flip: bool = False
    vertical_flip: bool = False
    fallback_to_simulator: bool = True


@dataclass(frozen=True)
class InferenceConfig:
    enabled: bool
    confidence_threshold: float


@dataclass(frozen=True)
class InspectionConfig:
    expected_label: str
    minimum_confidence: float
    minimum_objects: int
    maximum_objects: int


@dataclass(frozen=True)
class AppearanceConfig:
    theme: str = "dark"
    reduced_motion: bool = False


@dataclass(frozen=True)
class PathConfig:
    config_dir: Path
    log_dir: Path
    data_dir: Path


@dataclass(frozen=True)
class AppConfig:
    environment: str
    log_level: str
    paths: PathConfig
    plc: PlcConfig
    camera: CameraConfig
    inference: InferenceConfig
    inspection: InspectionConfig
    io_points: tuple[IoPoint, ...]
    appearance: AppearanceConfig = AppearanceConfig()


def load_config(
    project_root: Path,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    env = os.environ if environ is None else environ
    environment = env.get("HMI_YOLO_ENV", "development").strip().lower()
    if environment not in {"development", "production"}:
        raise ConfigurationError("HMI_YOLO_ENV debe ser development o production")

    config_file = project_root / "config" / f"{environment}.ini"
    parser = configparser.ConfigParser()
    if not parser.read(config_file, encoding="utf-8"):
        raise ConfigurationError(f"No se encontro la configuracion: {config_file}")
    parser.read(project_root / "config" / "runtime.ini", encoding="utf-8")

    try:
        mode_text = env.get("HMI_YOLO_PLC_MODE", parser.get("plc", "mode")).lower()
        mode = PlcMode(mode_text)
        host = env.get("HMI_YOLO_PLC_HOST", parser.get("plc", "host")).strip()
        port = int(env.get("HMI_YOLO_PLC_PORT", parser.get("plc", "port")))
        timeout = float(
            env.get("HMI_YOLO_PLC_TIMEOUT_SECONDS", parser.get("plc", "timeout_seconds"))
        )
        reconnect = float(
            env.get(
                "HMI_YOLO_PLC_RECONNECT_SECONDS",
                parser.get("plc", "reconnect_interval_seconds"),
            )
        )
        simulate_error = _parse_bool(
            env.get(
                "HMI_YOLO_SIMULATE_CONNECTION_ERROR",
                parser.get("plc", "simulate_connection_error"),
            )
        )
        log_level = env.get("HMI_YOLO_LOG_LEVEL", parser.get("application", "log_level"))
        paths = PathConfig(
            config_dir=_resolve_path(
                project_root,
                env.get("HMI_YOLO_CONFIG_DIR", parser.get("application", "config_dir")),
            ),
            log_dir=_resolve_path(
                project_root,
                env.get("HMI_YOLO_LOG_DIR", parser.get("application", "log_dir")),
            ),
            data_dir=_resolve_path(
                project_root,
                env.get("HMI_YOLO_DATA_DIR", parser.get("application", "data_dir")),
            ),
        )
        camera = CameraConfig(
            width=int(env.get("HMI_YOLO_CAMERA_WIDTH", parser.get("camera", "width"))),
            height=int(env.get("HMI_YOLO_CAMERA_HEIGHT", parser.get("camera", "height"))),
            frames_per_second=int(
                env.get("HMI_YOLO_CAMERA_FPS", parser.get("camera", "frames_per_second"))
            ),
            backend=CameraBackend(
                env.get("HMI_YOLO_CAMERA_BACKEND", parser.get("camera", "backend"))
            ),
            device=env.get("HMI_YOLO_CAMERA_DEVICE", parser.get("camera", "device")),
            sensor_id=int(env.get("HMI_YOLO_CAMERA_SENSOR_ID", parser.get("camera", "sensor_id"))),
            profile=CaptureProfile(
                env.get("HMI_YOLO_CAMERA_PROFILE", parser.get("camera", "profile"))
            ),
            pixel_format=env.get(
                "HMI_YOLO_CAMERA_PIXEL_FORMAT", parser.get("camera", "pixel_format")
            ),
            timeout_seconds=float(
                env.get("HMI_YOLO_CAMERA_TIMEOUT", parser.get("camera", "timeout_seconds"))
            ),
            reconnect_interval_seconds=float(
                env.get(
                    "HMI_YOLO_CAMERA_RECONNECT",
                    parser.get("camera", "reconnect_interval_seconds"),
                )
            ),
            buffer_count=int(
                env.get("HMI_YOLO_CAMERA_BUFFERS", parser.get("camera", "buffer_count"))
            ),
            rotation_degrees=int(
                env.get("HMI_YOLO_CAMERA_ROTATION", parser.get("camera", "rotation_degrees"))
            ),
            horizontal_flip=_parse_bool(
                env.get("HMI_YOLO_CAMERA_HFLIP", parser.get("camera", "horizontal_flip"))
            ),
            vertical_flip=_parse_bool(
                env.get("HMI_YOLO_CAMERA_VFLIP", parser.get("camera", "vertical_flip"))
            ),
            fallback_to_simulator=_parse_bool(
                env.get(
                    "HMI_YOLO_CAMERA_FALLBACK",
                    parser.get("camera", "fallback_to_simulator"),
                )
            ),
        )
        inference = InferenceConfig(
            enabled=_parse_bool(
                env.get("HMI_YOLO_INFERENCE_ENABLED", parser.get("inference", "enabled"))
            ),
            confidence_threshold=float(
                env.get(
                    "HMI_YOLO_CONFIDENCE_THRESHOLD",
                    parser.get("inference", "confidence_threshold"),
                )
            ),
        )
        inspection = InspectionConfig(
            expected_label=env.get(
                "HMI_YOLO_EXPECTED_LABEL", parser.get("inspection", "expected_label")
            ).strip(),
            minimum_confidence=float(
                env.get(
                    "HMI_YOLO_INSPECTION_CONFIDENCE",
                    parser.get("inspection", "minimum_confidence"),
                )
            ),
            minimum_objects=int(
                env.get(
                    "HMI_YOLO_MINIMUM_OBJECTS",
                    parser.get("inspection", "minimum_objects"),
                )
            ),
            maximum_objects=int(
                env.get(
                    "HMI_YOLO_MAXIMUM_OBJECTS",
                    parser.get("inspection", "maximum_objects"),
                )
            ),
        )
        io_points = _parse_io_points(parser)
        appearance = AppearanceConfig(
            theme=env.get("HMI_YOLO_THEME", parser.get("appearance", "theme")),
            reduced_motion=_parse_bool(
                env.get(
                    "HMI_YOLO_REDUCED_MOTION",
                    parser.get("appearance", "reduced_motion"),
                )
            ),
        )
    except (configparser.Error, KeyError, ValueError) as exc:
        raise ConfigurationError(f"Configuracion invalida: {exc}") from exc

    if not host:
        raise ConfigurationError("La direccion del PLC no puede estar vacia")
    if not 0 <= port <= 65535:
        raise ConfigurationError("El puerto debe estar entre 0 y 65535")
    if timeout <= 0 or reconnect <= 0:
        raise ConfigurationError("Los intervalos deben ser mayores que cero")
    if log_level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError("Nivel de logging no valido")
    if camera.width <= 0 or camera.height <= 0:
        raise ConfigurationError("La resolucion de camara debe ser positiva")
    if not 1 <= camera.frames_per_second <= 60:
        raise ConfigurationError("Los FPS de camara deben estar entre 1 y 60")
    if camera.timeout_seconds <= 0 or camera.reconnect_interval_seconds <= 0:
        raise ConfigurationError("Los tiempos de camara deben ser positivos")
    if not 1 <= camera.buffer_count <= 32:
        raise ConfigurationError("Los buffers de camara deben estar entre 1 y 32")
    if camera.rotation_degrees not in {0, 90, 180, 270}:
        raise ConfigurationError("La rotacion debe ser 0, 90, 180 o 270 grados")
    if not 0.0 <= inference.confidence_threshold <= 1.0:
        raise ConfigurationError("El umbral de confianza debe estar entre 0 y 1")
    if not inspection.expected_label:
        raise ConfigurationError("La clase esperada no puede estar vacia")
    if not 0.0 <= inspection.minimum_confidence <= 1.0:
        raise ConfigurationError("La confianza de inspeccion debe estar entre 0 y 1")
    if inspection.minimum_objects < 0 or inspection.maximum_objects < inspection.minimum_objects:
        raise ConfigurationError("El rango de objetos de inspeccion no es valido")
    if appearance.theme not in {"dark", "light", "high_contrast"}:
        raise ConfigurationError("Tema visual no valido")

    return AppConfig(
        environment=environment,
        log_level=log_level.upper(),
        paths=paths,
        plc=PlcConfig(mode, host, port, timeout, reconnect, simulate_error),
        camera=camera,
        inference=inference,
        inspection=inspection,
        io_points=io_points,
        appearance=appearance,
    )


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else project_root / path


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"valor booleano no valido: {value}")


def _parse_io_points(parser: configparser.ConfigParser) -> tuple[IoPoint, ...]:
    points: list[IoPoint] = []
    for section in parser.sections():
        if not section.startswith("io."):
            continue
        data_type = IoDataType(parser.get(section, "data_type"))
        points.append(
            IoPoint(
                logical_name=section.removeprefix("io."),
                tag=parser.get(section, "tag"),
                data_type=data_type,
                direction=IoDirection(parser.get(section, "direction")),
                writable=parser.getboolean(section, "writable"),
                value=_default_io_value(data_type),
            )
        )
    if not points:
        raise ConfigurationError("Debe existir al menos un punto de E/S")
    return tuple(points)


def _default_io_value(data_type: IoDataType) -> bool | int | float | str:
    defaults: dict[IoDataType, bool | int | float | str] = {
        IoDataType.BOOLEAN: False,
        IoDataType.INTEGER: 0,
        IoDataType.FLOAT: 0.0,
        IoDataType.TEXT: "",
    }
    return defaults[data_type]

