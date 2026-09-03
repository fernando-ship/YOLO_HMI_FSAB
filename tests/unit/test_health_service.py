from hmi_yolo_311d_fsab.domain.health import HealthStatus
from hmi_yolo_311d_fsab.services.health_service import HealthService


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


def test_heartbeat_becomes_unavailable_after_timeout() -> None:
    clock = FakeClock()
    service = HealthService(clock)
    service.register("CAMARA", 2.0)
    service.activate("CAMARA")

    clock.value = 1.9
    assert service.evaluate()[0].status is HealthStatus.HEALTHY
    clock.value = 2.1
    snapshot = service.evaluate()[0]
    assert snapshot.status is HealthStatus.UNAVAILABLE
    assert snapshot.message == "Heartbeat vencido"


def test_new_heartbeat_recovers_component() -> None:
    clock = FakeClock()
    service = HealthService(clock)
    service.register("INFERENCIA", 1.0)
    service.activate("INFERENCIA")
    clock.value = 2.0
    service.evaluate()

    service.heartbeat("INFERENCIA", "Frames procesados")

    assert service.snapshots()[0].status is HealthStatus.HEALTHY
    assert service.snapshots()[0].message == "Frames procesados"


def test_inactive_component_does_not_timeout() -> None:
    clock = FakeClock()
    service = HealthService(clock)
    service.register("PLC", 1.0)
    service.deactivate("PLC")
    clock.value = 100.0

    assert service.evaluate()[0].message == "Detenido"
