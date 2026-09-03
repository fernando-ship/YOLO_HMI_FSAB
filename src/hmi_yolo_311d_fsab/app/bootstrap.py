import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from hmi_yolo_311d_fsab.app.application import ApplicationController
from hmi_yolo_311d_fsab.domain.camera import CameraClient
from hmi_yolo_311d_fsab.domain.camera_device import CameraBackend
from hmi_yolo_311d_fsab.domain.inference import InferenceEngine
from hmi_yolo_311d_fsab.domain.inspection import InspectionRules
from hmi_yolo_311d_fsab.domain.plc import PlcClient
from hmi_yolo_311d_fsab.infrastructure.config import (
    AppConfig,
    ConfigurationError,
    PlcMode,
    load_config,
)
from hmi_yolo_311d_fsab.infrastructure.jsonl_inspection_store import JsonlInspectionStore
from hmi_yolo_311d_fsab.infrastructure.linux_camera_discovery import LinuxCameraDiscovery
from hmi_yolo_311d_fsab.infrastructure.logging_setup import configure_logging
from hmi_yolo_311d_fsab.infrastructure.omron_nx_client import OmronNxEtherNetIpClient
from hmi_yolo_311d_fsab.infrastructure.open_cv_camera import OpenCvCameraClient
from hmi_yolo_311d_fsab.infrastructure.simulated_camera import SimulatedCameraClient
from hmi_yolo_311d_fsab.infrastructure.simulated_inference import SimulatedInferenceEngine
from hmi_yolo_311d_fsab.infrastructure.simulated_plc import SimulatedPlcClient
from hmi_yolo_311d_fsab.infrastructure.windows_camera_discovery import WindowsCameraDiscovery
from hmi_yolo_311d_fsab.presentation.camera_worker import CameraWorker
from hmi_yolo_311d_fsab.presentation.main_window import MainWindow
from hmi_yolo_311d_fsab.presentation.plc_worker import PlcWorker
from hmi_yolo_311d_fsab.presentation.theme_manager import Theme, ThemeManager
from hmi_yolo_311d_fsab.services.alarm_service import AlarmService
from hmi_yolo_311d_fsab.services.camera_discovery_service import (
    CameraDiscovery,
    CameraDiscoveryService,
)
from hmi_yolo_311d_fsab.services.camera_service import CameraService
from hmi_yolo_311d_fsab.services.configuration_service import ConfigurationService
from hmi_yolo_311d_fsab.services.health_service import HealthService
from hmi_yolo_311d_fsab.services.history_service import HistoryService
from hmi_yolo_311d_fsab.services.hmi_service import HmiService
from hmi_yolo_311d_fsab.services.inference_service import InferenceService
from hmi_yolo_311d_fsab.services.inspection_service import InspectionService
from hmi_yolo_311d_fsab.services.plc_service import PlcService
from hmi_yolo_311d_fsab.services.production_service import ProductionService


def create_controller(
    project_root: Path,
    argv: Sequence[str] | None = None,
    config: AppConfig | None = None,
) -> ApplicationController:
    settings = load_config(project_root) if config is None else config
    configure_logging(settings.log_level, settings.paths.log_dir)
    client = _create_plc_client(settings)
    camera_client = _create_camera_client(settings)
    inference_engine = _create_inference_engine()
    plc_service = PlcService(client)
    camera_service = CameraService(camera_client)
    inference_service = InferenceService(
        inference_engine,
        settings.inference.confidence_threshold,
    )
    inspection_service = InspectionService(
        InspectionRules(
            expected_label=settings.inspection.expected_label,
            minimum_confidence=settings.inspection.minimum_confidence,
            minimum_objects=settings.inspection.minimum_objects,
            maximum_objects=settings.inspection.maximum_objects,
        )
    )
    production_service = ProductionService(
        plc_service,
        inspection_service,
        {point.logical_name: point.tag for point in settings.io_points},
    )
    inspection_store = JsonlInspectionStore(settings.paths.data_dir / "inspections", 7)
    inspection_store.purge_expired()
    hmi_service = HmiService(
        plc_service,
        camera_service,
        inference_service,
        inspection_service,
        production_service,
        inspection_store,
        simulated_plc=settings.plc.mode is PlcMode.SIMULATED,
        inference_enabled=settings.inference.enabled,
        camera_backend=settings.camera.backend.value,
    )
    existing_app = QApplication.instance()
    qt_app = (
        existing_app
        if isinstance(existing_app, QApplication)
        else QApplication(list(argv or sys.argv))
    )
    theme_manager = ThemeManager()
    theme_manager.apply(qt_app, Theme(settings.appearance.theme))
    window = MainWindow(
        hmi_service.get_state(),
        settings.io_points,
        reduced_motion=settings.appearance.reduced_motion,
    )
    worker = PlcWorker(hmi_service)
    camera_worker = CameraWorker(hmi_service, settings.camera.frames_per_second)
    health_service = HealthService()
    health_service.register("PLC", 3600.0)
    heartbeat_timeout = max(2.0, 3 / settings.camera.frames_per_second)
    health_service.register("CAMARA", heartbeat_timeout)
    health_service.register("INFERENCIA", heartbeat_timeout)
    camera_discovery: CameraDiscovery
    if sys.platform == "win32":
        camera_discovery = WindowsCameraDiscovery()
    else:
        camera_discovery = LinuxCameraDiscovery()
    return ApplicationController(
        qt_app,
        hmi_service,
        window,
        worker,
        camera_worker,
        QThread(),
        settings,
        ConfigurationService(project_root / "config" / "runtime.ini"),
        CameraDiscoveryService(camera_discovery),
        AlarmService(),
        theme_manager,
        health_service,
        HistoryService(inspection_store),
    )


def _create_plc_client(config: AppConfig) -> PlcClient:
    if config.plc.mode is PlcMode.REAL:
        return OmronNxEtherNetIpClient(config.plc.host, config.plc.port, config.plc.timeout_seconds)
    return SimulatedPlcClient(
        simulate_connection_error=config.plc.simulate_connection_error,
        initial_variables={point.tag: point.value for point in config.io_points},
    )


def _create_camera_client(config: AppConfig) -> CameraClient:
    if config.camera.backend is CameraBackend.OPENCV:
        return OpenCvCameraClient(
            config.camera.device,
            config.camera.width,
            config.camera.height,
            config.camera.frames_per_second,
        )
    if config.camera.backend is not CameraBackend.SIMULATED:
        if not config.camera.fallback_to_simulator:
            raise ConfigurationError(
                "La captura real requiere una camara conectada y un adaptador validado"
            )
        logging.getLogger(__name__).warning(
            "Backend %s aun no validado; se utilizara la camara simulada",
            config.camera.backend.value,
        )
    return SimulatedCameraClient(config.camera.width, config.camera.height)


def _create_inference_engine() -> InferenceEngine:
    return SimulatedInferenceEngine()

