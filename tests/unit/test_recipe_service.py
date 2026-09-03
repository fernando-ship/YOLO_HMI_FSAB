from pathlib import Path

import pytest

from hmi_yolo_311d_fsab.domain.inspection import InspectionClassRule
from hmi_yolo_311d_fsab.domain.recipe import InspectionRecipe, RecipeError
from hmi_yolo_311d_fsab.infrastructure.json_recipe_store import JsonRecipeStore
from hmi_yolo_311d_fsab.services.recipe_service import RecipeService


def recipe(identifier: str = "default") -> InspectionRecipe:
    return InspectionRecipe(identifier, "Pieza A", "pieza", 0.85, 1, 1, 85, 3, 500)


def test_recipe_round_trip_and_activation(tmp_path: Path) -> None:
    store = JsonRecipeStore(tmp_path / "recipes.json")
    service = RecipeService(store, recipe())
    copy = service.duplicate("default")
    service.activate(copy.identifier)

    restored = RecipeService(store, recipe())

    assert restored.active().identifier == copy.identifier
    assert len(restored.recipes()) == 2


def test_active_recipe_cannot_be_deleted(tmp_path: Path) -> None:
    service = RecipeService(JsonRecipeStore(tmp_path / "recipes.json"), recipe())

    with pytest.raises(RecipeError, match="activa"):
        service.delete("default")


def test_multiclass_rules_are_persisted(tmp_path: Path) -> None:
    store = JsonRecipeStore(tmp_path / "recipes.json")
    multiclass = InspectionRecipe(
        "multi",
        "Bolsa completa",
        "Bolsa",
        0.7,
        1,
        1,
        85,
        3,
        500,
        (
            InspectionClassRule("Bolsa", 0.7, 1, 1),
            InspectionClassRule("Label", 0.8, 1, 1),
            InspectionClassRule("QR CODE", 0.75, 1, 1),
        ),
    )
    RecipeService(store, multiclass)

    restored = RecipeService(store, multiclass).active()

    assert restored.class_rules == multiclass.class_rules
