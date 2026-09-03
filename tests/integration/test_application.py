from dataclasses import replace
from pathlib import Path

from pytestqt.qtbot import QtBot

from hmi_yolo_311d_fsab.app.bootstrap import create_controller
from hmi_yolo_311d_fsab.infrastructure.config import load_config
from hmi_yolo_311d_fsab.presentation.status_indicator import IndicatorState


def test_application_creation_and_safe_close(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)
    controller.start(show_window=False)

    assert controller.window.windowTitle() == "HMI_YOLO_311D_FSAB"
    assert controller.window.connect_button.isEnabled()
    assert not controller.window.disconnect_button.isEnabled()
    assert controller.window.camera_start_button.isEnabled()
    assert not controller.window.camera_stop_button.isEnabled()
    assert not controller.window.inspection_button.isEnabled()
    assert not controller.window.snapshot_button.isEnabled()
    assert controller.window.maintenance_page.health_table.rowCount() == 3
    assert not controller.window.plc_state_label.is_active()
    assert not controller.window.camera_state_label.is_active()
    assert controller.window.connect_button.property("actionRole") == "start"
    assert controller.window.camera_start_button.property("actionRole") == "start"
    assert controller.window.operation_page.equipment_group.title() == "1. Preparar equipos"
    assert controller.window.operation_page.camera_group.title() == "2. Verificar imagen"
    assert (
        controller.window.operation_page.inspection_group.title()
        == "3. Inspeccionar y confirmar resultado"
    )
    assert controller.window.inspection_button.property("actionRole") == "primary"
    assert controller.window.reset_counters_button.property("actionRole") == "utility"
    assert controller.window.plc_simulator_page.message.isEnabled()
    assert len(controller.window.plc_simulator_page._input_checks) == 10

    controller.window.close()


def test_sidebar_navigates_between_sections(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)

    assert controller.window.pages.currentWidget() is controller.window.operation_page
    controller.window.navigation.setCurrentRow(1)
    assert controller.window.pages.currentWidget() is controller.window.io_monitor
    controller.window.navigation.setCurrentRow(2)
    assert controller.window.pages.currentWidget() is controller.window.events_page
    controller.window.navigation.setCurrentRow(3)
    assert controller.window.pages.currentWidget() is controller.window.history_page
    controller.window.navigation.setCurrentRow(4)
    assert controller.window.pages.currentWidget() is controller.window.recipes_page
    controller.window.navigation.setCurrentRow(5)
    assert controller.window.pages.currentWidget() is controller.window.plc_simulator_page
    controller.window.navigation.setCurrentRow(6)
    assert controller.window.pages.currentWidget() is controller.window.alarms_page
    controller.window.navigation.setCurrentRow(7)
    assert controller.window.pages.currentWidget() is controller.window.configuration_page
    controller.window.navigation.setCurrentRow(8)
    assert controller.window.pages.currentWidget() is controller.window.maintenance_page


def test_error_creates_and_acknowledges_alarm(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)

    controller.window.show_error("Fallo simulado")
    assert controller.window.navigation.item(6).text() == "Alarmas (1)"
    assert controller.window.alarms_page.table.rowCount() == 1
    assert controller.window.plc_state_label.state() is IndicatorState.ERROR
    assert controller.window.connect_button.property("actionRole") == "retry"
    assert controller.window.connect_button.text() == "Reintentar"

    controller.window.alarm_acknowledge_all_requested.emit()
    assert controller.window.navigation.item(6).text() == "Alarmas (0)"


def test_connect_and_disconnect_through_window(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)
    controller.start(show_window=False)

    controller.window.connect_button.click()
    qtbot.waitUntil(controller.window.disconnect_button.isEnabled, timeout=2000)
    assert "CONNECTED" in controller.window.plc_state_label.text()
    assert controller.window.plc_state_label.is_active()

    controller.window.disconnect_button.click()
    qtbot.waitUntil(controller.window.connect_button.isEnabled, timeout=2000)
    assert "DISCONNECTED" in controller.window.plc_state_label.text()
    assert not controller.window.plc_state_label.is_active()
    controller.shutdown()


def test_simulated_camera_updates_view(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)
    controller.start(show_window=False)

    controller.window.camera_start_button.click()
    qtbot.waitUntil(controller.window.camera_stop_button.isEnabled, timeout=2000)
    qtbot.waitUntil(
        lambda: "pieza: 92%" in controller.window.detection_summary_label.text(),
        timeout=2000,
    )
    assert "RUNNING" in controller.window.camera_state_label.text()
    assert controller.window.camera_state_label.is_active()
    assert controller.window.snapshot_button.isEnabled()
    assert "RUNNING" in controller.window.inference_state_label.text()
    assert "pieza: 92%" in controller.window.detection_summary_label.text()

    assert not controller.window.inspection_button.isEnabled()
    controller.window.connect_button.click()
    qtbot.waitUntil(controller.window.inspection_button.isEnabled, timeout=2000)

    controller.window.inspection_button.click()
    qtbot.waitUntil(
        lambda: "INSPECCION: OK" in controller.window.inspection_result_label.text(),
        timeout=2000,
    )
    assert controller.window.counters_label.text() == "Total: 1 | OK: 1 | NOK: 0"

    controller.window.reset_counters_button.click()
    qtbot.waitUntil(
        lambda: controller.window.counters_label.text() == "Total: 0 | OK: 0 | NOK: 0",
        timeout=2000,
    )

    qtbot.waitUntil(controller.window.production_cycle_button.isEnabled, timeout=2000)
    controller.window.production_cycle_button.click()
    qtbot.waitUntil(controller.window.production_ack_button.isEnabled, timeout=2000)
    assert "WAITING_ACK" in controller.window.production_state_label.text()

    controller.window.production_ack_button.click()
    qtbot.waitUntil(controller.window.production_cycle_button.isEnabled, timeout=2000)
    assert "WAITING_TRIGGER" in controller.window.production_state_label.text()

    controller.window.camera_stop_button.click()
    qtbot.waitUntil(controller.window.camera_start_button.isEnabled, timeout=2000)
    assert "STOPPED" in controller.window.camera_state_label.text()
    assert not controller.window.camera_state_label.is_active()
    controller.shutdown()


def test_snapshot_saves_raw_png(qtbot: QtBot, tmp_path: Path) -> None:
    config = load_config(Path.cwd())
    config = replace(config, paths=replace(config.paths, data_dir=tmp_path))
    controller = create_controller(Path.cwd(), [], config)
    qtbot.addWidget(controller.window)
    controller.start(show_window=False)

    controller.window.camera_start_button.click()
    qtbot.waitUntil(controller.window.snapshot_button.isEnabled, timeout=2000)
    qtbot.waitUntil(
        lambda: "pieza: 92%" in controller.window.detection_summary_label.text(),
        timeout=2000,
    )
    controller.window.snapshot_button.click()
    qtbot.waitUntil(
        lambda: len(tuple((tmp_path / "captures").glob("*.png"))) == 1,
        timeout=2000,
    )

    saved = tuple((tmp_path / "captures").glob("*.png"))[0]
    assert saved.stat().st_size > 0
    assert controller.window.snapshot_count_label.text() == "Capturas: 1"
    controller.shutdown()


def test_calibration_inspects_without_plc_or_counters(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)
    controller.start(show_window=False)

    controller.window.operation_page.calibration_mode.setChecked(True)
    controller.window.camera_start_button.click()
    qtbot.waitUntil(controller.window.inspection_button.isEnabled, timeout=2000)
    qtbot.waitUntil(
        lambda: "pieza: 92%" in controller.window.detection_summary_label.text(), timeout=2000
    )
    controller.window.inspection_button.click()
    qtbot.waitUntil(
        lambda: "INSPECCION: OK" in controller.window.inspection_result_label.text(),
        timeout=2000,
    )

    assert controller.window.counters_label.text() == "Total: 0 | OK: 0 | NOK: 0"
    assert not controller.window.production_cycle_button.isEnabled()
    controller.shutdown()
