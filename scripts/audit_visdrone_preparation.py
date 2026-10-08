"""Audit raw-file preservation, image copies, labels and coordinate round trips."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(raw_root, derived_root, file_manifest):
    raw_root, derived_root = Path(raw_root), Path(derived_root)
    with Path(file_manifest).open() as handle:
        original = {row["path"]: row for row in map(json.loads, handle)}
    raw_files = {p.relative_to(raw_root).as_posix() for p in raw_root.rglob("*") if p.is_file()}
    require(raw_files == original.keys(), "Raw file inventory changed")
    for name, row in original.items():
        path = raw_root / name
        require(path.stat().st_size == row["size_bytes"] and digest(path) == row["sha256"],
                f"Raw file changed: {name}")
    manifest = json.loads((derived_root / "manifest.json").read_text())
    for name, expected in manifest["artifact_sha256"].items():
        require(digest(derived_root / name) == expected, f"Artifact hash mismatch: {name}")
    counts, categories, seen_images, seen_labels = {}, {}, set(), set()
    fields = ("x", "y", "width", "height", "score", "category", "truncation", "occlusion")
    with (derived_root / "annotations.jsonl").open() as handle:
        for record in map(json.loads, handle):
            split = record["source_split"]
            totals = counts.setdefault(split, Counter())
            classes = categories.setdefault(split, Counter())
            require(record["output_image"] not in seen_images and record["output_label"] not in seen_labels,
                    "Repeated converted pair")
            seen_images.add(record["output_image"])
            seen_labels.add(record["output_label"])
            for key in ("image", "annotation"):
                name = record[f"source_{key}"]
                require(record["input_sha256"][key] == original[name]["sha256"], f"Input hash mismatch: {name}")
            require(digest(derived_root / record["output_image"]) == record["input_sha256"]["image"], "Image copy changed")
            label_path = derived_root / record["output_label"]
            require(digest(label_path) == record["label_sha256"], "Label hash mismatch")
            labels = [line.split() for line in label_path.read_text().splitlines()]
            source_lines = (raw_root / record["source_annotation"]).read_text(encoding="utf-8-sig").splitlines()
            require(len(record["rows"]) == sum(bool(line.strip()) for line in source_lines), "Source row lost")
            width, height = record["image_size"]
            index = 0
            for row in record["rows"]:
                original_values = [float(v) for v in source_lines[row["line"] - 1].rstrip().rstrip(",").split(",")]
                require([row[field] for field in fields] == original_values, "Original row values changed")
                totals["source_rows"] += 1
                if row["width"] == 0 or row["height"] == 0:
                    require(row["yolo"] is None and row["exclusion_reason"] == "zero_area_bbox", "Zero-area row not recorded")
                    totals["excluded_zero_area_rows"] += 1
                elif row["score"] == 0 or row["category"] in (0, 11):
                    require(row["yolo"] is None, "Ignored/other row became a target")
                    totals["ignored_other_rows"] += 1
                else:
                    require(index < len(labels) and len(labels[index]) == 5, "Target label missing/malformed")
                    values = labels[index]
                    require(int(values[0]) == row["category"] - 1, "Class mapping mismatch")
                    cx, cy, w, h = map(float, values[1:])
                    require(all(math.isfinite(v) and 0 < v <= 1 for v in (cx, cy, w, h)), "Invalid normalized coordinate")
                    reconstructed = ((cx - w / 2) * width, (cy - h / 2) * height, w * width, h * height)
                    require(all(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)
                                for a, b in zip(reconstructed, (row["x"], row["y"], row["width"], row["height"]))),
                            "Coordinate round trip mismatch")
                    index += 1
                    totals["target_rows"] += 1
                    classes[values[0]] += 1
            require(index == len(labels), "Unexpected extra target labels")
            totals["images"] += 1
    actual_images = {p.relative_to(derived_root).as_posix() for p in (derived_root / "images").rglob("*") if p.is_file()}
    actual_labels = {p.relative_to(derived_root).as_posix() for p in (derived_root / "labels").rglob("*") if p.is_file()}
    require(actual_images == seen_images and actual_labels == seen_labels, "Derived inventory mismatch")
    for split, values in counts.items():
        for key in ("images", "source_rows", "target_rows", "excluded_zero_area_rows"):
            require(values[key] == manifest["splits"][split][key], f"Count mismatch: {split}/{key}")
    return {"schema_version": 1, "status": "passed", "scope": "hash_inventory_and_label_roundtrip",
            "raw_files_verified": len(raw_files), "splits": {s: dict(c) for s, c in counts.items()},
            "yolo_class_counts": {s: dict(c) for s, c in categories.items()},
            "coordinate_tolerance_pixels": {"absolute": 1e-9, "relative": 1e-12},
            "not_checked": ["trainer_loading", "official_evaluator", "near_duplicates", "model_metrics"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--derived-root", type=Path, required=True)
    parser.add_argument("--file-manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(not any(args.report.resolve().is_relative_to(p.resolve()) for p in (args.raw_root, args.derived_root)),
                "Report must be outside raw and derived roots")
        require(not args.report.exists() and not args.report.is_symlink(), "Report already exists")
        report = audit(args.raw_root, args.derived_root, args.file_manifest)
        with args.report.open("x") as handle:
            json.dump(report, handle, indent=2)
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, KeyError, IndexError) as exc:
        parser.exit(2, f"Audit failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
