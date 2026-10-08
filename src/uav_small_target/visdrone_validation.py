"""Read-only VisDrone DET checks, with optional image decoding and bbox review."""

from collections import Counter
import hashlib
from pathlib import Path
import warnings

from .visdrone_annotations import AnnotationRowError, parse_annotation_row


SPLIT_DIRECTORIES = {
    "train": "VisDrone2019-DET-train",
    "val": "VisDrone2019-DET-val",
    "test-dev": "VisDrone2019-DET-test-dev",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def validate_dataset(
    root: Path, splits: tuple[str, ...] = ("train", "val"), *,
    check_duplicates: bool = False, check_images: bool = False,
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

    decoder = None
    if check_images:
        try:
            from PIL import Image, __version__ as pillow_version
        except ImportError as exc:
            raise ValueError("--check-images requires Pillow; install requirements.txt") from exc
        decoder = {"name": "Pillow", "version": pillow_version}

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

        image_dimensions = {}
        image_counts = Counter()
        for path in images:
            if check_images:
                image_counts["attempted"] += 1
                try:
                    # Verify container integrity, then reopen to actually decode pixels.
                    # Keep Pillow's pixel limit and strict truncated-file defaults.
                    with warnings.catch_warnings():
                        warnings.simplefilter("error", Image.DecompressionBombWarning)
                        with Image.open(path, formats=("JPEG", "PNG")) as image:
                            if getattr(image, "n_frames", 1) != 1:
                                raise ValueError("Expected a single-frame DET image")
                            image.verify()
                        with Image.open(path, formats=("JPEG", "PNG")) as image:
                            image.load()
                            image_dimensions[path] = image.size
                    image_counts["decoded"] += 1
                except (OSError, SyntaxError, ValueError, Image.DecompressionBombWarning,
                        Image.DecompressionBombError) as exc:
                    image_counts["failed"] += 1
                    issue("error", "image_decode_error", split, path, str(exc))
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
            dimensions = None
            matches = image_stems.get(path.stem, [])
            if len(matches) == 1 and len(annotation_stems[path.stem]) == 1:
                dimensions = image_dimensions.get(matches[0])
            try:
                with path.open(encoding="utf-8-sig") as handle:
                    nonblank = False
                    for line_number, text in enumerate(handle, start=1):
                        if not text.strip():
                            continue
                        nonblank = True
                        counts["nonblank_rows"] += 1
                        try:
                            row = parse_annotation_row(text)
                        except AnnotationRowError as exc:
                            for code, message in exc.issues:
                                issue("error", code, split, path, message, line_number)
                            continue
                        x, y, width, height = row.x, row.y, row.width, row.height
                        score, category = row.score, row.category
                        truncation, occlusion = row.truncation, row.occlusion
                        counts["valid_core_rows"] += 1
                        categories[str(category)] += 1
                        if score == 0 or category in (0, 11):
                            counts["ignored_or_other_rows"] += 1
                        else:
                            counts["target_rows"] += 1
                        if x < 0 or y < 0:
                            issue("warning", "negative_bbox_origin", split, path, "Review boundary/truncation convention; no clipping performed", line_number)
                        if check_images:
                            if dimensions is None:
                                counts["bbox_rows_skipped"] += 1
                            else:
                                counts["bbox_rows_checked"] += 1
                                image_width, image_height = dimensions
                                if x < 0 or y < 0 or x + width > image_width or y + height > image_height:
                                    counts["bbox_rows_outside"] += 1
                                    issue(
                                        "warning", "bbox_outside_image", split, path,
                                        f"BBox exceeds raw {image_width}x{image_height} pixel extent; review original convention, no clipping performed",
                                        line_number,
                                    )
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
            "image_decoding": {
                key: image_counts[key] for key in ("attempted", "decoded", "failed")
            } if check_images else None,
            "bbox_boundaries": {
                key: counts[f"bbox_rows_{key}"] for key in ("checked", "skipped", "outside")
            } if check_images else None,
        }

    errors = sum(item["severity"] == "error" for item in issues)
    warning_count = sum(item["severity"] == "warning" for item in issues)
    return {
        "schema_version": 2,
        "status": "failed" if errors else "warning" if warning_count else "passed",
        "scope": "file_pairing_annotation_metadata_and_images" if check_images else "file_pairing_and_annotation_metadata_only",
        "duplicate_check": "sha256_exact_bytes" if check_duplicates else "not_run",
        "image_check": "pillow_verify_and_load" if check_images else "not_run",
        "decoder": decoder,
        "bbox_check": (
            "partial" if any(s["bbox_boundaries"]["skipped"] for s in summaries.values())
            else "completed"
        ) if check_images else "not_run",
        "bbox_coordinate_policy": "raw_pixels_xywh_no_exif_transform_or_clipping" if check_images else None,
        "not_checked": ([] if check_images else ["full_image_decoding", "bbox_vs_image_dimensions"]) + [
            "near_duplicate_or_scene_leakage",
            "archive_integrity", "release_identity_and_terms", "official_evaluator_equivalence",
            "model_metrics",
        ],
        "splits": summaries, "summary": {"errors": errors, "warnings": warning_count},
        "issues": issues,
    }
