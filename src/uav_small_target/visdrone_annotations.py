"""Shared, dependency-free interpretation of original VisDrone DET GT rows."""

from dataclasses import dataclass
import math


CATEGORY_NAMES = (
    "ignored regions", "pedestrian", "people", "bicycle", "car", "van",
    "truck", "tricycle", "awning-tricycle", "bus", "motor", "others",
)


class AnnotationRowError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("; ".join(message for _, message in issues))


@dataclass(frozen=True)
class Annotation:
    x: float
    y: float
    width: float
    height: float
    score: int
    category: int
    truncation: int
    occlusion: int

    @property
    def kind(self):
        if self.score == 0 or self.category == 0:
            return "ignored"
        return "other" if self.category == 11 else "target"


def parse_annotation_row(text: str, *, allow_zero_area: bool = False) -> Annotation:
    """Parse GT metadata; zero-area rows are opt-in for audited exclusion only.

    Validator/preview keep strict defaults. Negative extents always fail.
    """
    fields = [field.strip() for field in text.strip().split(",")]
    if len(fields) == 9 and fields[-1] == "":
        fields.pop()
    if len(fields) != 8:
        raise AnnotationRowError([("field_count", "Expected 8 fields")])
    try:
        values = [float(field) for field in fields]
    except ValueError as exc:
        raise AnnotationRowError([("non_numeric", "All fields must be numeric")]) from exc
    if not all(math.isfinite(value) for value in values):
        raise AnnotationRowError([("non_finite", "NaN/Infinity are not allowed")])
    if not all(value.is_integer() for value in values[4:]):
        raise AnnotationRowError([("non_integer_metadata", "Metadata fields must be integers")])
    score, category, truncation, occlusion = map(int, values[4:])
    errors = []
    if score not in (0, 1):
        errors.append(("invalid_score", "GT score must be 0 or 1"))
    if category not in range(12):
        errors.append(("invalid_category", "Category must be in 0..11"))
    if (values[2] < 0 or values[3] < 0
            or (not allow_zero_area and (values[2] == 0 or values[3] == 0))):
        errors.append(("invalid_bbox_size", "BBox width and height must be positive"))
    if errors:
        raise AnnotationRowError(errors)
    return Annotation(*values[:4], score, category, truncation, occlusion)
