import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from hmi_yolo_311d_fsab.domain.inspection import (
    InspectionResult,
    InspectionStatus,
    StoredInspection,
)


class JsonlInspectionStore:
    """Almacen local compacto, diario y con retencion limitada."""

    _PREFIX = "inspections-"
    _SUFFIX = ".jsonl"

    def __init__(self, directory: Path, retention_days: int = 7) -> None:
        if retention_days < 1:
            raise ValueError("La retencion debe ser de al menos un dia")
        self._directory = directory
        self._retention_days = retention_days

    def save(self, result: InspectionResult, *, source: str) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        self.purge_expired()
        target = self._directory / (
            f"{self._PREFIX}{result.inspected_at.date().isoformat()}{self._SUFFIX}"
        )
        record = {
            "frame_sequence": result.frame_sequence,
            "status": result.status.value,
            "reason": result.reason,
            "inspected_at": result.inspected_at.isoformat(),
            "elapsed_ms": round(result.elapsed_ms, 3),
            "source": source,
        }
        with target.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")

    def purge_expired(self) -> int:
        if not self._directory.exists():
            return 0
        today = datetime.now(timezone.utc).date()
        oldest_allowed = today - timedelta(days=self._retention_days - 1)
        removed = 0
        for path in self._directory.glob(f"{self._PREFIX}*{self._SUFFIX}"):
            file_date = self._date_from_name(path)
            if file_date is not None and file_date < oldest_allowed:
                path.unlink()
                removed += 1
        return removed

    def load(self) -> tuple[StoredInspection, ...]:
        self.purge_expired()
        records: list[StoredInspection] = []
        if not self._directory.exists():
            return ()
        for path in sorted(self._directory.glob(f"{self._PREFIX}*{self._SUFFIX}")):
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    try:
                        raw = json.loads(line)
                        records.append(
                            StoredInspection(
                                frame_sequence=int(raw["frame_sequence"]),
                                status=InspectionStatus(str(raw["status"])),
                                reason=str(raw["reason"]),
                                inspected_at=datetime.fromisoformat(raw["inspected_at"]),
                                elapsed_ms=float(raw["elapsed_ms"]),
                                source=str(raw["source"]),
                            )
                        )
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                        continue
        return tuple(sorted(records, key=lambda item: item.inspected_at, reverse=True))

    def clear(self) -> int:
        if not self._directory.exists():
            return 0
        paths = tuple(self._directory.glob(f"{self._PREFIX}*{self._SUFFIX}"))
        for path in paths:
            path.unlink()
        return len(paths)

    def storage_bytes(self) -> int:
        if not self._directory.exists():
            return 0
        return sum(
            path.stat().st_size for path in self._directory.glob(f"{self._PREFIX}*{self._SUFFIX}")
        )

    def _date_from_name(self, path: Path) -> date | None:
        value = path.name.removeprefix(self._PREFIX).removesuffix(self._SUFFIX)
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
