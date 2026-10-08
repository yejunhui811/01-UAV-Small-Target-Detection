"""Read-only checks for VisDrone DET file pairing and annotation metadata.

This module does not decode images, convert labels, or measure model performance.
"""

from collections import Counter
import hashlib
import math
from pathlib import Path


SPLIT_DIRECTORIES = {
    "train": "VisDrone2019-DET-train",
    "val": "VisDrone2019-DET-val",
    "test-dev": "VisDrone2019-DET-test-dev",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def validate_dataset(
    root: Path, splits: tuple[str, ...] = ("train", "val"), *,
    check_duplicates: bool = False,
) -> dict:
    """Inspect selected labeled DET splits and return a JSON-serializable report.

    Root must contain the official split directories. Unknown/repeated splits
    raise ValueError. Issues in dataset files are collected instead of repaired.
    """
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"Dataset root does not exist or is not a directory: {root}")
    if not splits or len(set(splits)) != len(splits):
        raise ValueError("Choose at least one split; repeated splits are not allowed")
    if any(split not in SPLIT_DIRECTORIES for split in splits):
        raise ValueError("Supported labeled splits are train, val, test-dev")

    issues = []
    summaries = {}
    seen_hashes = {}

    def issue(severity, code, split, path, message, line=None):
        entry = {
            "severity": severity, "code": code, "split": split,
            "path": path.relative_to(root).as_posix(), "message": message,
        }
        if line is not None:
            entry["line"] = line
        issues.append(entry)

    def inventory(directory, suffixes, split):
        if not directory.is_dir():
            issue("error", "missing_directory", split, directory, "Required directory is missing")
            return [], {}
        try:
            paths = sorted(
                (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in suffixes),
                key=lambda p: p.name,
            )
        except OSError as exc:
            issue("error", "directory_read_error", split, directory, str(exc))
            return [], {}
        grouped = {}
        for path in paths:
            grouped.setdefault(path.stem, []).append(path)
        for stem, matches in grouped.items():
            if len(matches) > 1:
                issue("error", "ambiguous_stem", split, matches[0], f"Multiple files use stem {stem!r}")
        return paths, grouped

    for split in splits:
        split_root = root / SPLIT_DIRECTORIES[split]
        images, image_stems = inventory(split_root / "images", IMAGE_SUFFIXES, split)
        annotations, annotation_stems = inventory(split_root / "annotations", {".txt"}, split)
        if not images:
            issue("error", "empty_images", split, split_root / "images", "No supported image files found")
        if not annotations:
            issue("error", "empty_annotations", split, split_root / "annotations", "No annotation TXT files found")
        for stem in sorted(image_stems.keys() - annotation_stems.keys()):
            issue("error", "missing_annotation", split, image_stems[stem][0], "No matching annotation stem")
        for stem in sorted(annotation_stems.keys() - image_stems.keys()):
            issue("error", "missing_image", split, annotation_stems[stem][0], "No matching image stem")

        for path in images:
            try:
                if path.stat().st_size == 0:
                    issue("error", "empty_image", split, path, "Image file has zero bytes")
                    continue
                if check_duplicates:
                    with path.open("rb") as handle:
                        digest = hashlib.file_digest(handle, "sha256").hexdigest()
                    if digest in seen_hashes:
                        prior_split, prior_path = seen_hashes[digest]
                        cross_split = prior_split != split
                        issue(
                            "error" if cross_split else "warning",
                            "cross_split_duplicate" if cross_split else "within_split_duplicate",
                            split, path,
                            f"Identical file bytes to {prior_path.relative_to(root).as_posix()}",
                        )
                    else:
                        seen_hashes[digest] = (split, path)
            except OSError as exc:
                issue("error", "image_read_error", split, path, str(exc))

        counts = Counter()
        categories = Counter()
        for path in annotations:
            try:
                with path.open(encoding="utf-8-sig") as handle:
                    nonblank = False
                    for line_number, text in enumerate(handle, start=1):
                        if not text.strip():
                            continue
                        nonblank = True
                        counts["nonblank_rows"] += 1
                        fields = [field.strip() for field in text.strip().split(",")]
                        # Accept one optional terminal delimiter, not extra columns.
                        if len(fields) == 9 and fields[-1] == "":
                            fields.pop()
                        if len(fields) != 8:
                            issue("error", "field_count", split, path, "Expected 8 fields", line_number)
                            continue
                        try:
                            values = [float(field) for field in fields]
                        except ValueError:
                            issue("error", "non_numeric", split, path, "All fields must be numeric", line_number)
                            continue
                        if not all(math.isfinite(value) for value in values):
                            issue("error", "non_finite", split, path, "NaN/Infinity are not allowed", line_number)
                            continue
                        x, y, width, height, score, category, truncation, occlusion = values
                        if not all(value.is_integer() for value in values[4:]):
                            issue("error", "non_integer_metadata", split, path, "Metadata fields must be integers", line_number)
                            continue
                        score, category, truncation, occlusion = map(int, values[4:])
                        invalid = False
                        if score not in (0, 1):
                            issue("error", "invalid_score", split, path, "GT score must be 0 or 1", line_number)
                            invalid = True
                        if category not in range(12):
                            issue("error", "invalid_category", split, path, "Category must be in 0..11", line_number)
                            invalid = True
                        if width <= 0 or height <= 0:
                            issue("error", "invalid_bbox_size", split, path, "BBox width and height must be positive", line_number)
                            invalid = True
                        if invalid:
                            continue
                        counts["valid_core_rows"] += 1
                        categories[str(category)] += 1
                        if score == 0 or category in (0, 11):
                            counts["ignored_or_other_rows"] += 1
                        else:
                            counts["target_rows"] += 1
                        if x < 0 or y < 0:
                            issue("warning", "negative_bbox_origin", split, path, "Review boundary/truncation convention; no clipping performed", line_number)
                        if truncation not in (0, 1) or occlusion not in (0, 1, 2):
                            issue("warning", "unusual_attributes", split, path, "Review truncation/occlusion values against original release; row preserved", line_number)
                    if not nonblank:
                        issue("warning", "empty_annotation", split, path, "Empty annotation may be a negative image; review before training")
            except (OSError, UnicodeError) as exc:
                issue("error", "annotation_read_error", split, path, str(exc))

        summaries[split] = {
            "images": len(images), "annotations": len(annotations),
            "matched_pairs": sum(
                len(image_stems[stem]) == len(annotation_stems[stem]) == 1
                for stem in image_stems.keys() & annotation_stems.keys()
            ),
            "nonblank_rows": counts["nonblank_rows"],
            "valid_core_rows": counts["valid_core_rows"],
            "target_rows": counts["target_rows"],
            "ignored_or_other_rows": counts["ignored_or_other_rows"],
            "original_category_counts": dict(sorted(categories.items(), key=lambda item: int(item[0]))),
        }

    errors = sum(item["severity"] == "error" for item in issues)
    warnings = sum(item["severity"] == "warning" for item in issues)
    return {
        "schema_version": 1,
        "status": "failed" if errors else "warning" if warnings else "passed",
        "scope": "file_pairing_and_annotation_metadata_only",
        "duplicate_check": "sha256_exact_bytes" if check_duplicates else "not_run",
        "not_checked": [
            "full_image_decoding", "bbox_vs_image_dimensions", "near_duplicate_or_scene_leakage",
            "archive_integrity", "release_identity_and_terms", "official_evaluator_equivalence",
            "model_metrics",
        ],
        "splits": summaries, "summary": {"errors": errors, "warnings": warnings},
        "issues": issues,
    }
