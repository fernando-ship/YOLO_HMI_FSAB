from dataclasses import replace
from datetime import datetime, timezone

from hmi_yolo_311d_fsab.domain.alarm import Alarm, AlarmSeverity, AlarmState


class AlarmService:
    def __init__(self) -> None:
        self._alarms: list[Alarm] = []
        self._next_identifier = 1

    def raise_alarm(self, source: str, message: str, severity: AlarmSeverity) -> Alarm:
        alarm = Alarm(
            self._next_identifier,
            source,
            message,
            severity,
            AlarmState.ACTIVE,
            datetime.now(timezone.utc),
        )
        self._next_identifier += 1
        self._alarms.append(alarm)
        return alarm

    def acknowledge(self, identifier: int) -> Alarm:
        return self._change_state(identifier, AlarmState.ACKNOWLEDGED)

    def acknowledge_all(self) -> tuple[Alarm, ...]:
        self._alarms = [
            replace(alarm, state=AlarmState.ACKNOWLEDGED)
            if alarm.state is AlarmState.ACTIVE
            else alarm
            for alarm in self._alarms
        ]
        return self.get_alarms()

    def resolve(self, identifier: int) -> Alarm:
        return self._change_state(identifier, AlarmState.RESOLVED)

    def get_alarms(self) -> tuple[Alarm, ...]:
        return tuple(self._alarms)

    def active_count(self) -> int:
        return sum(alarm.state is AlarmState.ACTIVE for alarm in self._alarms)

    def _change_state(self, identifier: int, state: AlarmState) -> Alarm:
        for index, alarm in enumerate(self._alarms):
            if alarm.identifier == identifier:
                updated = replace(alarm, state=state)
                self._alarms[index] = updated
                return updated
        raise KeyError(f"Alarma inexistente: {identifier}")
