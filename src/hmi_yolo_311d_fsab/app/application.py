import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from hmi_yolo_311d_fsab.domain.alarm import AlarmSeverity
from hmi_yolo_311d_fsab.domain.camera import CameraState
from hmi_yolo_311d_fsab.domain.health import HealthStatus
from hmi_yolo_311d_fsab.domain.inference import InferenceState
from hmi_yolo_311d_fsab.domain.plc import ConnectionState
from hmi_yolo_311d_fsab.infrastructure.config import AppConfig
from hmi_yolo_311d_fsab.presentation.camera_worker import CameraWorker
from hmi_yolo_311d_fsab.presentation.main_window import MainWindow
from hmi_yolo_311d_fsab.presentation.plc_worker import PlcWorker
from hmi_yolo_311d_fsab.presentation.settings_dialog import SettingsDialog
from hmi_yolo_311d_fsab.presentation.theme_manager import Theme, ThemeManager
from hmi_yolo_311d_fsab.services.alarm_service import AlarmService
from hmi_yolo_311d_fsab.services.camera_discovery_service import CameraDiscoveryService
from hmi_yolo_311d_fsab.services.configuration_service import ConfigurationService
from hmi_yolo_311d_fsab.services.health_service import HealthService
from hmi_yolo_311d_fsab.services.history_service import HistoryService
from hmi_yolo_311d_fsab.services.hmi_service import HmiService, HmiState


class ApplicationController(QObject):
    shutdown_requested = Signal()

    def __init__(
        self,
        qt_app: QApplication,
        hmi_service: HmiService,
        window: MainWindow,
        worker: PlcWorker,
        camera_worker: CameraWorker,
        worker_thread: QThread,
        config: AppConfig,
        configuration_service: ConfigurationService,
        camera_discovery_service: CameraDiscoveryService,
        alarm_service: AlarmService,
        theme_manager: ThemeManager,
        health_service: HealthService,
        history_service: HistoryService,
    ) -> None:
        super().__init__()
        self._qt_app = qt_app
        self._hmi_service = hmi_service
        self.window = window
        self._worker = worker
        self._camera_worker = camera_worker
        self._worker_thread = worker_thread
        self._config = config
        self._configuration_service = configuration_service
        self._camera_discovery_service = camera_discovery_service
        self._alarm_service = alarm_service
        self._theme_manager = theme_manager
        self._health_service = health_service
        self._history_service = history_service
        self._health_alerted: set[str] = set()
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(1000)
        self._health_timer.timeout.connect(self.check_health)
        self._stopped = False
        self._logger = logging.getLogger(__name__)

        worker.moveToThread(worker_thread)
        camera_worker.moveToThread(worker_thread)
        window.connect_requested.connect(worker.connect_plc)
        window.disconnect_requested.connect(worker.disconnect_plc)
        worker.state_changed.connect(window.apply_state)
        worker.state_changed.connect(self.observe_state)
        worker.operation_failed.connect(self.handle_plc_error)
        worker.io_updated.connect(window.show_plc_snapshot)
        window.camera_start_requested.connect(camera_worker.start_camera)
        window.camera_stop_requested.connect(camera_worker.stop_camera)
        camera_worker.frame_ready.connect(window.show_frame)
        camera_worker.frame_ready.connect(self.record_frame_heartbeat)
        camera_worker.state_changed.connect(window.apply_state)
        camera_worker.state_changed.connect(self.observe_state)
        camera_worker.operation_failed.connect(window.show_camera_error)
        camera_worker.inspection_failed.connect(window.show_inspection_error)
        window.inspection_requested.connect(camera_worker.inspect_latest)
        window.counters_reset_requested.connect(camera_worker.reset_counters)
        camera_worker.inspection_ready.connect(window.show_inspection)
        camera_worker.inspection_ready.connect(self.refresh_history)
        camera_worker.counters_reset.connect(window.show_counters)
        window.production_cycle_requested.connect(camera_worker.run_simulated_cycle)
        window.production_acknowledge_requested.connect(camera_worker.acknowledge_cycle)
        camera_worker.production_cycle_ready.connect(window.show_production_cycle)
        camera_worker.production_cycle_ready.connect(self.refresh_history)
        camera_worker.production_acknowledged.connect(window.show_production_acknowledged)
        self.shutdown_requested.connect(worker.shutdown)
        self.shutdown_requested.connect(camera_worker.shutdown)
        window.closing.connect(self.shutdown)
        qt_app.aboutToQuit.connect(self.shutdown)
        window.settings_requested.connect(self.open_settings)
        window.alarm_reported.connect(self.report_alarm)
        window.alarm_acknowledge_requested.connect(self.acknowledge_alarm)
        window.alarm_acknowledge_all_requested.connect(self.acknowledge_all_alarms)
        window.history_page.export_requested.connect(self.export_history)
        window.history_page.clear_requested.connect(self.clear_history)
        window.snapshot_requested.connect(self.save_snapshot)

    def start(self, *, show_window: bool = True) -> None:
        self._hmi_service.start()
        self._worker_thread.start()
        self._health_timer.start()
        self.check_health()
        self.refresh_history()
        if show_window:
            self.window.show()
        self._logger.info("Aplicacion iniciada")

    def run(self) -> int:
        self.start()
        return self._qt_app.exec()

    @Slot()
    def open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._camera_discovery_service)
        if dialog.exec():
            updated = dialog.build_config()
            try:
                self._configuration_service.save(updated)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self.window, "Configuracion invalida", str(exc))
                return
            self._config = updated
            self._theme_manager.apply(self._qt_app, Theme(updated.appearance.theme))
            self.window.set_reduced_motion(updated.appearance.reduced_motion)
            self.window.show_configuration_saved()

    @Slot(str, str, str)
    def report_alarm(self, source: str, message: str, severity: str) -> None:
        self._alarm_service.raise_alarm(source, message, AlarmSeverity(severity))
        self._refresh_alarms()

    @Slot(int)
    def acknowledge_alarm(self, identifier: int) -> None:
        self._alarm_service.acknowledge(identifier)
        self._refresh_alarms()

    @Slot()
    def acknowledge_all_alarms(self) -> None:
        self._alarm_service.acknowledge_all()
        self._refresh_alarms()

    def _refresh_alarms(self) -> None:
        self.window.set_alarms(self._alarm_service.get_alarms(), self._alarm_service.active_count())

    @Slot(str)
    def handle_plc_error(self, message: str) -> None:
        self.window.show_error(message)
        answer = QMessageBox.question(
            self.window,
            "PLC desconectado",
            f"{message}\n\n¿Desea reintentar la conexion?",
            QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
        )
        if answer is QMessageBox.StandardButton.Retry:
            QTimer.singleShot(0, self.window.connect_requested.emit)

    @Slot()
    @Slot(object, object)
    def refresh_history(self, _first: object = None, _second: object = None) -> None:
        try:
            self.window.history_page.set_records(
                self._history_service.records(), self._history_service.storage_bytes()
            )
        except OSError as exc:
            self.window.events_page.append(f"ERROR HISTORIAL: {exc}")

    @Slot(object)
    def export_history(self, records: object) -> None:
        selected = records if isinstance(records, tuple) else ()
        target, _ = QFileDialog.getSaveFileName(
            self.window, "Exportar historial", "historial_inspecciones.csv", "CSV (*.csv)"
        )
        if not target:
            return
        try:
            self._history_service.export_csv(Path(target), selected)
            self.window.events_page.append(f"Historial exportado: {target}")
        except OSError as exc:
            QMessageBox.warning(self.window, "No fue posible exportar", str(exc))

    @Slot()
    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self.window,
            "Limpiar historial",
            "¿Eliminar todos los resultados locales? Esta accion no se puede deshacer.",
        )
        if answer is not QMessageBox.StandardButton.Yes:
            return
        try:
            removed = self._history_service.clear()
            self.refresh_history()
            self.window.events_page.append(f"Historial limpiado: {removed} archivos eliminados")
        except OSError as exc:
            QMessageBox.warning(self.window, "No fue posible limpiar", str(exc))

    @Slot(object, int)
    def save_snapshot(self, image: object, frame_sequence: int) -> None:
        if not isinstance(image, QImage):
            self.window.show_snapshot_error("El frame recibido no es una imagen valida")
            return
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = (
            self._config.paths.data_dir
            / "captures"
            / f"capture-{timestamp}-frame-{frame_sequence:06d}.png"
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not image.save(str(target)):
                raise OSError("Qt no pudo codificar la imagen PNG")
        except (OSError, ValueError) as exc:
            self.window.show_snapshot_error(str(exc))
            return
        self.window.show_snapshot_saved(target)

    @Slot(object)
    def observe_state(self, state: HmiState) -> None:
        if state.plc_state is ConnectionState.CONNECTED:
            self._health_service.heartbeat("PLC", "Conectado")
        else:
            self._health_service.deactivate("PLC", state.plc_state.value)
        if state.camera_state is CameraState.RUNNING:
            self._health_service.activate("CAMARA", "Capturando")
        else:
            self._health_service.deactivate("CAMARA", state.camera_state.value)
        if state.inference_state is InferenceState.RUNNING:
            self._health_service.activate("INFERENCIA", "Procesando")
        else:
            self._health_service.deactivate("INFERENCIA", state.inference_state.value)
        self.window.set_health(self._health_service.snapshots())

    @Slot(object, object, object)
    def record_frame_heartbeat(
        self, _image: object, _raw_image: object, _result: object
    ) -> None:
        self._health_service.heartbeat("CAMARA", "Frames recibidos")
        self._health_service.heartbeat("INFERENCIA", "Frames procesados")

    @Slot()
    def check_health(self) -> None:
        snapshots = self._health_service.evaluate()
        for snapshot in snapshots:
            timed_out = (
                snapshot.status is HealthStatus.UNAVAILABLE
                and snapshot.message == "Heartbeat vencido"
            )
            if timed_out and snapshot.component not in self._health_alerted:
                self._health_alerted.add(snapshot.component)
                self.report_alarm(
                    snapshot.component,
                    "Se perdio el heartbeat del servicio",
                    AlarmSeverity.WARNING.value,
                )
            elif snapshot.status is HealthStatus.HEALTHY:
                self._health_alerted.discard(snapshot.component)
        self.window.set_health(snapshots)

    @Slot()
    def shutdown(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._health_timer.stop()
        if self._worker_thread.isRunning():
            shutdown_loop = QEventLoop()
            remaining_workers = 2

            def worker_stopped() -> None:
                nonlocal remaining_workers
                remaining_workers -= 1
                if remaining_workers == 0:
                    shutdown_loop.quit()

            self._worker.shutdown_completed.connect(worker_stopped)
            self._camera_worker.shutdown_completed.connect(worker_stopped)
            self.shutdown_requested.emit()
            shutdown_loop.exec()
            self._worker_thread.quit()
            self._worker_thread.wait()
        else:
            self._hmi_service.stop()
        self._logger.info("Aplicacion cerrada")

