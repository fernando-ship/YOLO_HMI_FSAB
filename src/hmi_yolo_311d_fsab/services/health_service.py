from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from hmi_yolo_311d_fsab.domain.health import HealthSnapshot, HealthStatus


@dataclass
class _ComponentState:
    timeout_seconds: float
    active: bool = False
    last_heartbeat: float | None = None
    status: HealthStatus = HealthStatus.UNAVAILABLE
    message: str = "Detenido"


class HealthService:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._components: dict[str, _ComponentState] = {}

    def register(self, component: str, timeout_seconds: float) -> None:
        if timeout_seconds <= 0:
            raise ValueError("El timeout de salud debe ser positivo")
        self._components[component] = _ComponentState(timeout_seconds)

    def activate(self, component: str, message: str = "Operativo") -> None:
        state = self._get(component)
        state.active = True
        state.last_heartbeat = self._clock()
        state.status = HealthStatus.HEALTHY
        state.message = message

    def deactivate(self, component: str, message: str = "Detenido") -> None:
        state = self._get(component)
        state.active = False
        state.status = HealthStatus.UNAVAILABLE
        state.message = message

    def heartbeat(self, component: str, message: str = "Operativo") -> None:
        self.activate(component, message)

    def mark_degraded(self, component: str, message: str) -> None:
        state = self._get(component)
        state.status = HealthStatus.DEGRADED
        state.message = message

    def evaluate(self) -> tuple[HealthSnapshot, ...]:
        now = self._clock()
        for state in self._components.values():
            if (
                state.active
                and state.last_heartbeat is not None
                and now - state.last_heartbeat > state.timeout_seconds
            ):
                state.status = HealthStatus.UNAVAILABLE
                state.message = "Heartbeat vencido"
        return self.snapshots()

    def snapshots(self) -> tuple[HealthSnapshot, ...]:
        return tuple(
            HealthSnapshot(name, state.status, state.message, state.last_heartbeat)
            for name, state in self._components.items()
        )

    def _get(self, component: str) -> _ComponentState:
        try:
            return self._components[component]
        except KeyError as exc:
            raise KeyError(f"Componente de salud no registrado: {component}") from exc
