from dataclasses import replace
from typing import Protocol

from hmi_yolo_311d_fsab.domain.recipe import InspectionRecipe, RecipeError


class RecipeStore(Protocol):
    def load(self) -> tuple[tuple[InspectionRecipe, ...], str | None]: ...

    def save(self, recipes: tuple[InspectionRecipe, ...], active_id: str) -> None: ...


class RecipeService:
    def __init__(self, store: RecipeStore, default: InspectionRecipe) -> None:
        self._store = store
        recipes, active_id = store.load()
        self._recipes = recipes or (default,)
        self._active_id = active_id or self._recipes[0].identifier
        if not any(item.identifier == self._active_id for item in self._recipes):
            self._active_id = self._recipes[0].identifier
        self._persist()

    def recipes(self) -> tuple[InspectionRecipe, ...]:
        return self._recipes

    def active(self) -> InspectionRecipe:
        return next(item for item in self._recipes if item.identifier == self._active_id)

    def get(self, identifier: str) -> InspectionRecipe:
        return self._find(identifier)

    def save(self, recipe: InspectionRecipe) -> None:
        self._validate(recipe)
        existing = {item.identifier: item for item in self._recipes}
        existing[recipe.identifier] = recipe
        self._recipes = tuple(sorted(existing.values(), key=lambda item: item.name.lower()))
        self._persist()

    def duplicate(self, identifier: str) -> InspectionRecipe:
        source = self._find(identifier)
        suffix = 2
        new_id = f"{source.identifier}_copy"
        while any(item.identifier == new_id for item in self._recipes):
            new_id = f"{source.identifier}_copy_{suffix}"
            suffix += 1
        copy = replace(source, identifier=new_id, name=f"{source.name} copia")
        self.save(copy)
        return copy

    def activate(self, identifier: str) -> InspectionRecipe:
        recipe = self._find(identifier)
        self._active_id = identifier
        self._persist()
        return recipe

    def delete(self, identifier: str) -> None:
        if identifier == self._active_id:
            raise RecipeError("No se puede eliminar la receta activa")
        self._find(identifier)
        self._recipes = tuple(item for item in self._recipes if item.identifier != identifier)
        self._persist()

    def _find(self, identifier: str) -> InspectionRecipe:
        try:
            return next(item for item in self._recipes if item.identifier == identifier)
        except StopIteration as exc:
            raise RecipeError(f"No existe la receta '{identifier}'") from exc

    @staticmethod
    def _validate(recipe: InspectionRecipe) -> None:
        if (
            not recipe.identifier.strip()
            or not recipe.name.strip()
            or not recipe.expected_label.strip()
        ):
            raise RecipeError("Identificador, nombre y clase son obligatorios")
        if not 0 <= recipe.minimum_confidence <= 1:
            raise RecipeError("La confianza debe estar entre 0 y 1")
        if recipe.minimum_objects < 0 or recipe.maximum_objects < recipe.minimum_objects:
            raise RecipeError("El rango de objetos no es valido")
        active_rules = [rule for rule in recipe.class_rules if rule.enabled]
        if recipe.class_rules and not active_rules:
            raise RecipeError("Debe habilitar al menos una clase requerida")
        labels = [rule.label.strip() for rule in active_rules]
        if any(not label for label in labels) or len(labels) != len(set(labels)):
            raise RecipeError("Las clases requeridas deben tener nombres unicos")
        if any(
            not 0 <= rule.minimum_confidence <= 1
            or rule.minimum_objects < 0
            or rule.maximum_objects < rule.minimum_objects
            for rule in active_rules
        ):
            raise RecipeError("Una regla de clase no es valida")
        if not 0 <= recipe.quality_threshold_percent <= 100:
            raise RecipeError("La calidad debe estar entre 0 y 100")
        if recipe.cycle_timeout_seconds <= 0 or recipe.maximum_frame_age_ms <= 0:
            raise RecipeError("Los tiempos deben ser positivos")

    def _persist(self) -> None:
        self._store.save(self._recipes, self._active_id)
