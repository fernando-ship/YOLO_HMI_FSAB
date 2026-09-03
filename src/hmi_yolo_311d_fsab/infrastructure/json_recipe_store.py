import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hmi_yolo_311d_fsab.domain.inspection import InspectionClassRule
from hmi_yolo_311d_fsab.domain.recipe import InspectionRecipe


class JsonRecipeStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> tuple[tuple[InspectionRecipe, ...], str | None]:
        if not self._path.exists():
            return (), None
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        recipes = tuple(self._deserialize(item) for item in raw.get("recipes", []))
        active = raw.get("active_recipe_id")
        return recipes, str(active) if active is not None else None

    def save(self, recipes: tuple[InspectionRecipe, ...], active_id: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "active_recipe_id": active_id,
            "recipes": [asdict(recipe) for recipe in recipes],
        }
        temporary = self._path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self._path)

    @staticmethod
    def _deserialize(item: dict[str, Any]) -> InspectionRecipe:
        values = dict(item)
        raw_rules = values.get("class_rules", [])
        values["class_rules"] = tuple(
            InspectionClassRule(**rule) for rule in raw_rules if isinstance(rule, dict)
        )
        return InspectionRecipe(**values)
