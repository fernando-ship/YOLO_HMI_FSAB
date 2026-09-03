from pytestqt.qtbot import QtBot

from hmi_yolo_311d_fsab.domain.io_points import IoDataType, IoDirection, IoPoint
from hmi_yolo_311d_fsab.presentation.io_monitor import IoMonitor
from hmi_yolo_311d_fsab.presentation.status_indicator import IndicatorState, StatusIndicator


def test_status_indicator_switches_between_black_and_bright_green(qtbot: QtBot) -> None:
    indicator = StatusIndicator("ESTADO")
    qtbot.addWidget(indicator)

    assert not indicator.is_active()
    assert StatusIndicator.OFF_COLOR in indicator.lamp.styleSheet()

    indicator.set_active(True)

    assert indicator.is_active()
    assert StatusIndicator.ON_COLOR in indicator.lamp.styleSheet()

    indicator.set_state(IndicatorState.WARNING)
    assert indicator.state() is IndicatorState.WARNING
    assert StatusIndicator.WARNING_COLOR in indicator.lamp.styleSheet()

    indicator.set_state(IndicatorState.ERROR)
    assert indicator.state() is IndicatorState.ERROR
    assert StatusIndicator.ERROR_COLOR in indicator.lamp.styleSheet()


def test_io_monitor_uses_indicators_only_for_boolean_points(qtbot: QtBot) -> None:
    points = (
        IoPoint("input_01", "Input01", IoDataType.BOOLEAN, IoDirection.INPUT, False, False),
        IoPoint("counter", "Counter", IoDataType.INTEGER, IoDirection.INPUT, False, 3),
    )
    monitor = IoMonitor(points, simulated=True)
    qtbot.addWidget(monitor)

    boolean_indicator = monitor.cellWidget(0, IoMonitor.VALUE_COLUMN)
    assert isinstance(boolean_indicator, StatusIndicator)
    assert boolean_indicator.text() == "OFF"
    assert not boolean_indicator.is_active()
    assert monitor.item(0, IoMonitor.VALUE_COLUMN).text() == ""
    assert monitor.cellWidget(1, IoMonitor.VALUE_COLUMN) is None

    monitor.update_values({"input_01": True, "counter": 4})

    assert boolean_indicator.text() == "ON"
    assert boolean_indicator.is_active()
    assert monitor.item(0, IoMonitor.VALUE_COLUMN).text() == ""
    assert monitor.item(1, IoMonitor.VALUE_COLUMN).text() == "4"
