import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hmi_yolo_311d_fsab.domain.inspection import InspectionResult, InspectionStatus
from hmi_yolo_311d_fsab.infrastructure.jsonl_inspection_store import JsonlInspectionStore


def test_saves_compact_daily_jsonl(tmp_path: Path) -> None:
    store = JsonlInspectionStore(tmp_path, retention_days=7)
    inspected_at = datetime.now(timezone.utc)
    result = InspectionResult(8, InspectionStatus.OK, "Correcto", inspected_at, 1.23456)

    store.save(result, source="manual")

    target = tmp_path / f"inspections-{inspected_at.date().isoformat()}.jsonl"
    record = json.loads(target.read_text(encoding="utf-8"))
    assert record["frame_sequence"] == 8
    assert record["status"] == "ok"
    assert record["source"] == "manual"
    assert "rgb_data" not in record
    loaded = store.load()
    assert loaded[0].frame_sequence == 8
    assert loaded[0].source == "manual"
    assert store.storage_bytes() > 0


def test_purges_files_outside_seven_day_window(tmp_path: Path) -> None:
    today = datetime.now(timezone.utc).date()
    expired = tmp_path / f"inspections-{today - timedelta(days=7)}.jsonl"
    retained = tmp_path / f"inspections-{today - timedelta(days=6)}.jsonl"
    expired.write_text("{}\n", encoding="utf-8")
    retained.write_text("{}\n", encoding="utf-8")

    removed = JsonlInspectionStore(tmp_path, retention_days=7).purge_expired()

    assert removed == 1
    assert not expired.exists()
    assert retained.exists()


def test_clear_removes_only_inspection_files(tmp_path: Path) -> None:
    inspection = tmp_path / "inspections-2026-01-01.jsonl"
    unrelated = tmp_path / "notes.txt"
    inspection.write_text("{}\n", encoding="utf-8")
    unrelated.write_text("keep", encoding="utf-8")

    assert JsonlInspectionStore(tmp_path).clear() == 1
    assert unrelated.exists()

