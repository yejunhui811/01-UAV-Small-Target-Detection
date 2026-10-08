"""Strict local VisDrone DET to YOLO conversion; no downloads or model calls."""

from collections import Counter
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
from pathlib import Path
import platform
import shutil
import tempfile
import warnings

from .visdrone_annotations import AnnotationRowError, CATEGORY_NAMES, parse_annotation_row
from .visdrone_validation import IMAGE_SUFFIXES, SPLIT_DIRECTORIES


CONVERSION_VERSION = "visdrone-yolo-v2"
OUTPUT_SPLITS = {"train": "train", "val": "val", "test-dev": "test"}


def _digest(content):
    return hashlib.sha256(content).hexdigest()


def _inventory(directory, suffixes):
    if not directory.is_dir():
        raise ValueError(f"Missing directory: {directory}")
    paths, folded_stems = {}, set()
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        # Portable output names: reject case collisions even on Linux.
        if path.stem.casefold() in folded_stems:
            raise ValueError(f"Ambiguous filename stem: {path}")
        if "\\" in path.name or any(ord(c) < 32 for c in path.name):
            raise ValueError(f"Unsupported filename: {path.name!r}")
        paths[path.stem] = path
        folded_stems.add(path.stem.casefold())
    if not paths:
        raise ValueError(f"No supported files in {directory}")
    return paths


def convert_dataset(root: Path, output_dir: Path, splits=("train", "val"), *,
                    synthetic=False, zero_area_policy="reject") -> dict:
    """Copy images, emit target labels and preserve every valid GT row in JSONL.

    Requires train+val; test-dev is optional and mapped to test. Every pair must
    decode and every nonblank row must parse. Target boxes must fit raw pixels.
    Validation failures discard only temporary staging, without publishing.
    Publication reserves a new directory exclusively; write failure may leave
    an incomplete new output. Existing outputs and raw sources are never edited.
    """
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("Output directory already exists; choose a new directory")
    root, output_dir = Path(root).resolve(), output_dir.resolve()
    splits = tuple(splits)
    if zero_area_policy not in ("reject", "exclude"):
        raise ValueError("zero_area_policy must be reject or exclude")
    if not root.is_dir():
        raise ValueError("Choose an existing raw dataset root")
    if (len(splits) != len(set(splits)) or not {"train", "val"}.issubset(splits)
            or any(split not in OUTPUT_SPLITS for split in splits)):
        raise ValueError("Choose train and val, optionally test-dev; no repeated splits")
    splits = tuple(split for split in OUTPUT_SPLITS if split in splits)
    if output_dir.is_relative_to(root) or root.is_relative_to(output_dir):
        raise ValueError("Raw root and output directory must be separate, non-nested paths")
    if output_dir.exists():
        raise ValueError("Output directory already exists; choose a new directory")
    try:
        from PIL import Image, __version__ as pillow_version
    except ImportError as exc:
        raise ValueError("Conversion requires Pillow; install requirements.txt") from exc

    # At most one image/TXT pair is held in memory; generated artifacts stay on disk.
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    totals, split_counts = Counter(), {}
    with tempfile.TemporaryDirectory(prefix=".uav-convert-", dir=output_dir.parent) as temporary:
        stage = Path(temporary)
        with (stage / "annotations.jsonl").open("w", encoding="utf-8") as records:
            for split in splits:
                split_root = root / SPLIT_DIRECTORIES[split]
                images = _inventory(split_root / "images", IMAGE_SUFFIXES)
                annotations = _inventory(split_root / "annotations", {".txt"})
                if images.keys() != annotations.keys():
                    raise ValueError(f"{split}: image/annotation stems do not match")
                destination = OUTPUT_SPLITS[split]
                for directory in ("images", "labels"):
                    (stage / directory / destination).mkdir(parents=True)
                counts = Counter()
                for stem, image_path in images.items():
                    annotation_path = annotations[stem]
                    context = f"{split}/{annotation_path.name}"
                    image_bytes = image_path.read_bytes()
                    annotation_bytes = annotation_path.read_bytes()
                    try:
                        text = annotation_bytes.decode("utf-8-sig")
                        with warnings.catch_warnings():
                            warnings.simplefilter("error", Image.DecompressionBombWarning)
                            with Image.open(BytesIO(image_bytes), formats=("JPEG", "PNG")) as image:
                                if getattr(image, "n_frames", 1) != 1:
                                    raise ValueError("Expected a single-frame DET image")
                                image.verify()
                            with Image.open(BytesIO(image_bytes), formats=("JPEG", "PNG")) as image:
                                image.load()  # Keep raw EXIF coordinates and original bytes.
                                if image.getexif().get(274, 1) != 1:
                                    raise ValueError("Nonidentity EXIF orientation requires an explicit trainer coordinate policy")
                                width, height = image.size
                    except (OSError, SyntaxError, ValueError, UnicodeError,
                            Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
                        raise ValueError(f"{context}: source decoding failed: {exc}") from exc
                    labels, rows, issues = [], [], []
                    for line, raw in enumerate(text.splitlines(), 1):
                        if not raw.strip():
                            continue
                        try:
                            row = parse_annotation_row(raw, allow_zero_area=zero_area_policy == "exclude")
                        except AnnotationRowError as exc:
                            raise ValueError(f"{context}:{line}: {exc}") from exc
                        counts["source_rows"] += 1
                        if row.truncation not in (0, 1) or row.occlusion not in (0, 1, 2):
                            issues.append({"line": line, "code": "unusual_attributes"})
                        converted, exclusion_reason = None, None
                        if row.width == 0 or row.height == 0:
                            counts["excluded_zero_area_rows"] += 1
                            exclusion_reason = "zero_area_bbox"
                            issues.append({"line": line, "code": "excluded_zero_area_bbox"})
                        elif row.kind == "target":
                            right, bottom = row.x + row.width, row.y + row.height
                            if row.x < 0 or row.y < 0 or right > width or bottom > height:
                                raise ValueError(f"{context}:{line}: target bbox outside raw image; no clipping")
                            if right <= row.x or bottom <= row.y:
                                raise ValueError(f"{context}:{line}: target bbox extent lost in float arithmetic")
                            xywh = [(row.x + row.width / 2) / width,
                                    (row.y + row.height / 2) / height,
                                    row.width / width, row.height / height]
                            if not all(0 < value <= 1 for value in xywh):
                                raise ValueError(f"{context}:{line}: normalized bbox is not representable")
                            converted = {"class_id": row.category - 1, "xywh": xywh}
                            labels.append(f"{row.category - 1} " + " ".join(format(v, ".17g") for v in xywh) + "\n")
                            counts["target_rows"] += 1
                        else:
                            counts[f"{row.kind}_rows"] += 1
                            exclusion_reason = row.kind
                        rows.append({"line": line, **asdict(row), "kind": row.kind,
                                     "category_name": CATEGORY_NAMES[row.category], "yolo": converted,
                                     "exclusion_reason": exclusion_reason})
                    if not labels:
                        counts["empty_label_images"] += 1
                        issues.append({"code": "empty_target_labels_review_before_training"})
                    if any(row["kind"] != "target" for row in rows):
                        issues.append({"code": "excluded_rows_do_not_define_trainer_ignore_regions"})
                    image_relative = f"images/{destination}/{image_path.name}"
                    label_relative = f"labels/{destination}/{stem}.txt"
                    label_bytes = "".join(labels).encode("utf-8")
                    (stage / image_relative).write_bytes(image_bytes)
                    (stage / label_relative).write_bytes(label_bytes)
                    records.write(json.dumps({
                        "source_split": split, "output_split": destination,
                        "source_image": image_path.relative_to(root).as_posix(),
                        "source_annotation": annotation_path.relative_to(root).as_posix(),
                        "image_size": [width, height], "input_sha256": {
                            "image": _digest(image_bytes), "annotation": _digest(annotation_bytes)},
                        "output_image": image_relative, "output_label": label_relative,
                        "label_sha256": _digest(label_bytes), "rows": rows, "issues": issues,
                    }, ensure_ascii=False, allow_nan=False) + "\n")
                    counts["images"] += 1
                    counts["warnings"] += len(issues)
                split_counts[split] = {key: counts[key] for key in (
                    "images", "source_rows", "target_rows", "ignored_rows", "other_rows",
                    "excluded_zero_area_rows", "empty_label_images", "warnings")}
                totals.update(counts)

        # JSON double-quoted scalars are valid YAML; no YAML package needed to emit.
        yaml = "# Local conversion; no automatic download hook\npath: " + json.dumps(str(output_dir), ensure_ascii=False) + "\n"
        yaml += "".join(f"{OUTPUT_SPLITS[s]}: images/{OUTPUT_SPLITS[s]}\n" for s in splits)
        yaml += "names:\n" + "".join(f"  {c - 1}: {json.dumps(CATEGORY_NAMES[c])}\n" for c in range(1, 11))
        (stage / "dataset.yaml").write_text(yaml, encoding="utf-8")
        manifest = {
            "schema_version": 1, "conversion_version": CONVERSION_VERSION,
            "status": "converted_with_warnings" if totals["warnings"] else "converted",
            "scope": "local_label_conversion_not_training_or_evaluation",
            "source_kind": "synthetic_demo" if synthetic else "local_unverified_data",
            "environment": {"python": platform.python_version(), "pillow": pillow_version},
            "class_mapping": {str(c): c - 1 for c in range(1, 11)},
            "split_mapping": {s: OUTPUT_SPLITS[s] for s in splits},
            "policies": {
                "bbox": "raw_pixel_xywh_to_normalized_center_xywh_no_clip_or_exif_transform",
                "ignored_other": "exclude_from_yolo_preserve_all_rows_in_annotations_jsonl",
                "images": "copy_original_bytes_no_move_or_mask",
                "exif": "require_identity_orientation",
                "precision": "17_significant_digits_positive_normalized_extents",
                "invalid_row_or_target_bbox": "abort_without_publishing_output",
                "zero_area": "exclude_and_record" if zero_area_policy == "exclude" else "reject",
            },
            "splits": split_counts,
            "not_checked": ["release_identity_and_terms", "exact_duplicates_and_scene_leakage", "trainer_loading",
                            "training_ignore_regions", "official_evaluator_equivalence", "model_metrics"],
            "artifact_sha256": {},
        }
        for name in ("annotations.jsonl", "dataset.yaml"):
            with (stage / name).open("rb") as handle:
                manifest["artifact_sha256"][name] = hashlib.file_digest(handle, "sha256").hexdigest()
        (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        output_dir.mkdir()  # Exclusive reservation; refuse even a concurrent empty directory.
        for artifact in sorted(stage.iterdir()):
            shutil.move(str(artifact), str(output_dir / artifact.name))
    return manifest
