from dataclasses import dataclass

from hmi_yolo_311d_fsab.domain.inspection import InspectionClassRule


@dataclass(frozen=True)
class InspectionRecipe:
    identifier: str
    name: str
    expected_label: str
    minimum_confidence: float
    minimum_objects: int
    maximum_objects: int
    quality_threshold_percent: float
    cycle_timeout_seconds: float
    maximum_frame_age_ms: int
    class_rules: tuple[InspectionClassRule, ...] = ()


class RecipeError(ValueError):
    """La operacion solicitada sobre recetas no es valida."""
