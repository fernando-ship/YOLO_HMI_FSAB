import csv
from pathlib import Path

from hmi_yolo_311d_fsab.domain.inspection import InspectionResultStore, StoredInspection


class HistoryService:
    def __init__(self, store: InspectionResultStore) -> None:
        self._store = store

    def records(self) -> tuple[StoredInspection, ...]:
        return self._store.load()

    def storage_bytes(self) -> int:
        return self._store.storage_bytes()

    def clear(self) -> int:
        return self._store.clear()

    def export_csv(self, target: Path, records: tuple[StoredInspection, ...]) -> None:
        with target.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["fecha_utc", "resultado", "frame", "duracion_ms", "origen", "motivo"])
            for record in records:
                writer.writerow(
                    [
                        record.inspected_at.isoformat(),
                        record.status.value,
                        record.frame_sequence,
                        f"{record.elapsed_ms:.3f}",
                        record.source,
                        record.reason,
                    ]
                )
