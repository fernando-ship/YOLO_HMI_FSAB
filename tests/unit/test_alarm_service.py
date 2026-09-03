from hmi_yolo_311d_fsab.domain.alarm import AlarmSeverity, AlarmState
from hmi_yolo_311d_fsab.services.alarm_service import AlarmService


def test_alarm_lifecycle_and_active_count() -> None:
    service = AlarmService()
    first = service.raise_alarm("PLC", "Sin comunicacion", AlarmSeverity.ERROR)
    second = service.raise_alarm("CAMARA", "Sin frames", AlarmSeverity.WARNING)

    assert first.identifier == 1
    assert second.identifier == 2
    assert service.active_count() == 2
    assert service.acknowledge(first.identifier).state is AlarmState.ACKNOWLEDGED
    assert service.active_count() == 1
    assert service.resolve(second.identifier).state is AlarmState.RESOLVED
    assert service.active_count() == 0


def test_acknowledge_all_preserves_resolved_alarms() -> None:
    service = AlarmService()
    first = service.raise_alarm("PLC", "Error", AlarmSeverity.ERROR)
    second = service.raise_alarm("CAMARA", "Error", AlarmSeverity.ERROR)
    service.resolve(first.identifier)

    alarms = service.acknowledge_all()

    assert alarms[0].state is AlarmState.RESOLVED
    assert alarms[1].state is AlarmState.ACKNOWLEDGED
    assert second.identifier == 2
