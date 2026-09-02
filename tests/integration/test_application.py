from pathlib import Path

from pytestqt.qtbot import QtBot

from hmi_yolo_311d_fsab.app.bootstrap import create_controller


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
    assert controller.window.maintenance_page.health_table.rowCount() == 3

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
    assert controller.window.pages.currentWidget() is controller.window.alarms_page
    controller.window.navigation.setCurrentRow(5)
    assert controller.window.pages.currentWidget() is controller.window.configuration_page
    controller.window.navigation.setCurrentRow(6)
    assert controller.window.pages.currentWidget() is controller.window.maintenance_page


def test_error_creates_and_acknowledges_alarm(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)

    controller.window.show_error("Fallo simulado")
    assert controller.window.navigation.item(4).text() == "Alarmas (1)"
    assert controller.window.alarms_page.table.rowCount() == 1

    controller.window.alarm_acknowledge_all_requested.emit()
    assert controller.window.navigation.item(4).text() == "Alarmas (0)"


def test_connect_and_disconnect_through_window(qtbot: QtBot) -> None:
    controller = create_controller(Path.cwd(), [])
    qtbot.addWidget(controller.window)
    controller.start(show_window=False)

    controller.window.connect_button.click()
    qtbot.waitUntil(controller.window.disconnect_button.isEnabled, timeout=2000)
    assert "CONNECTED" in controller.window.plc_state_label.text()

    controller.window.disconnect_button.click()
    qtbot.waitUntil(controller.window.connect_button.isEnabled, timeout=2000)
    assert "DISCONNECTED" in controller.window.plc_state_label.text()
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
    assert "COMPLETED" in controller.window.production_state_label.text()

    controller.window.production_ack_button.click()
    qtbot.waitUntil(controller.window.production_cycle_button.isEnabled, timeout=2000)
    assert "WAITING_TRIGGER" in controller.window.production_state_label.text()

    controller.window.camera_stop_button.click()
    qtbot.waitUntil(controller.window.camera_start_button.isEnabled, timeout=2000)
    assert "STOPPED" in controller.window.camera_state_label.text()
    controller.shutdown()

