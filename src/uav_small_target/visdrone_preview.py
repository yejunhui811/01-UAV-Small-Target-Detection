"""Single-pair annotation review; never modifies raw files or measures metrics."""

from dataclasses import asdict
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import warnings

from .visdrone_annotations import AnnotationRowError, CATEGORY_NAMES, parse_annotation_row
from .visdrone_validation import IMAGE_SUFFIXES, SPLIT_DIRECTORIES


COLORS = {
    "target": (34, 197, 94), "ignored": (245, 158, 11),
    "other": (168, 85, 247), "outside": (239, 68, 68),
}


def preview_annotations(root: Path, split: str, image_stem: str, output_dir: Path,
                        *, synthetic: bool = False) -> dict:
    """Save preview.png + manifest.json in a new directory outside raw root.

    Invalid rows produce a partial preview and are reported, never repaired.
    Bboxes use unrotated raw pixel xywh; only the display intersection is drawn.
    """
    root, output_dir = Path(root).resolve(), Path(output_dir).resolve()
    if not root.is_dir() or split not in SPLIT_DIRECTORIES:
        raise ValueError("Choose an existing raw root and labeled train/val/test-dev split")
    if not image_stem or image_stem in (".", "..") or "/" in image_stem or "\\" in image_stem:
        raise ValueError("image-stem must be a plain filename stem")
    if output_dir.is_relative_to(root):
        raise ValueError("Output directory must be outside the dataset root")
    if output_dir.exists():
        raise ValueError("Output directory already exists; choose a new directory")
    split_root = root / SPLIT_DIRECTORIES[split]

    def match(directory, suffixes):
        if not directory.is_dir():
            raise ValueError(f"Required directory is missing: {directory.name}")
        paths = [p for p in directory.iterdir()
                 if p.is_file() and p.stem == image_stem and p.suffix.lower() in suffixes]
        if len(paths) != 1:
            raise ValueError(f"Expected one matching {directory.name} file; found {len(paths)}")
        return paths[0]

    image_path = match(split_root / "images", IMAGE_SUFFIXES)
    annotation_path = match(split_root / "annotations", {".txt"})
    try:
        from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version
    except ImportError as exc:
        raise ValueError("Preview requires Pillow; install requirements.txt") from exc
    image_bytes, annotation_bytes = image_path.read_bytes(), annotation_path.read_bytes()
    try:
        text = annotation_bytes.decode("utf-8-sig")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes), formats=("JPEG", "PNG")) as original:
                if getattr(original, "n_frames", 1) != 1:
                    raise ValueError("Expected a single-frame DET image")
                original.verify()
            with Image.open(BytesIO(image_bytes), formats=("JPEG", "PNG")) as original:
                original.load()
                image = original.convert("RGB")  # No EXIF transpose or resize.
    except (OSError, SyntaxError, ValueError, UnicodeError, Image.DecompressionBombWarning,
            Image.DecompressionBombError) as exc:
        raise ValueError(f"Could not decode source pair: {exc}") from exc

    width, height = image.size
    rows, issues = [], []
    nonblank = 0

    def issue(severity, code, message, line=None):
        entry = {"severity": severity, "code": code, "message": message}
        if line is not None:
            entry["line"] = line
        issues.append(entry)

    for line, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        nonblank += 1
        try:
            row = parse_annotation_row(raw)
        except AnnotationRowError as exc:
            for code, message in exc.issues:
                issue("error", code, message, line)
            continue
        right, bottom = row.x + row.width, row.y + row.height
        outside = row.x < 0 or row.y < 0 or right > width or bottom > height
        if outside:
            issue("warning", "bbox_outside_image", "Review raw coordinate convention; annotation not clipped", line)
        if row.truncation not in (0, 1) or row.occlusion not in (0, 1, 2):
            issue("warning", "unusual_attributes", "Review original truncation/occlusion values", line)
        # xywh denotes a continuous extent; Pillow rectangle endpoints are inclusive.
        visible = None
        if right <= row.x or bottom <= row.y:
            issue("warning", "bbox_display_precision", "Positive bbox extent is lost in float arithmetic; display skipped", line)
        elif row.x < width and row.y < height and right > 0 and bottom > 0:
            visible = [
                math.floor(max(0, row.x)), math.floor(max(0, row.y)),
                math.ceil(min(width, right)) - 1, math.ceil(min(height, bottom)) - 1,
            ]
        color_key = "outside" if outside else row.kind
        rows.append({
            "line": line, **asdict(row), "category_name": CATEGORY_NAMES[row.category],
            "kind": row.kind, "outside_image": outside,
            "display_bbox_xyxy": visible, "display_color": color_key,
        })
    if not nonblank:
        issue("warning", "empty_annotation", "Empty annotation may represent a negative image")
    errors = sum(i["severity"] == "error" for i in issues)
    warning_count = sum(i["severity"] == "warning" for i in issues)
    status = "partial" if errors else "warning" if warning_count else "ready"

    margin, top, panel_width = 24, 96, 380
    sidebar_rows = rows[:20]
    canvas_size = (max(800, width + panel_width + margin * 3),
                   max(height, 110 + len(sidebar_rows) * 42) + top + 80)
    if Image.MAX_IMAGE_PIXELS and canvas_size[0] * canvas_size[1] > Image.MAX_IMAGE_PIXELS:
        raise ValueError("Preview canvas exceeds Pillow pixel limit")
    canvas = Image.new("RGB", canvas_size, (15, 23, 42))
    canvas.paste(image, (margin, top))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=14)
    title_font = ImageFont.load_default(size=23)
    title = "SYNTHETIC DEMO - annotation preview" if synthetic else "VisDrone annotation preview"
    draw.text((margin, 18), title, font=title_font, fill="white")
    draw.text((margin, 53), f"{split}/{image_path.name} | {width}x{height} raw pixels | {status.upper()}",
              font=font, fill=(203, 213, 225))
    # Draw on a separate image so text/lines outside raw bounds never enter the sidebar.
    overlay = image.copy()
    overlay_draw = ImageDraw.Draw(overlay)
    for row in rows:
        bbox = row["display_bbox_xyxy"]
        if bbox is None:
            continue
        color = COLORS[row["display_color"]]
        shortest_side = min(bbox[2] - bbox[0] + 1, bbox[3] - bbox[1] + 1)
        # Thick Pillow outlines can spill outside tiny boxes; keep their footprint.
        if shortest_side == 1:
            overlay_draw.line(bbox, fill=color, width=1)
        else:
            overlay_draw.rectangle(bbox, outline=color, width=1 if shortest_side < 4 else 2)
        label = f"L{row['line']} {row['category']}:{row['category_name']}"
        text_box = overlay_draw.textbbox((0, 0), label, font=font)
        label_width = text_box[2] - text_box[0]
        label_x = max(0, min(bbox[0], width - label_width))
        label_y = bbox[1] - 18 if bbox[1] >= 18 else bbox[3] + 1
        if label_width <= width and label_y + 18 <= height:
            overlay_draw.rectangle((label_x, label_y, label_x + label_width, label_y + 17), fill=(15, 23, 42))
            overlay_draw.text((label_x, label_y), label, font=font, fill=color)
    canvas.paste(overlay, (margin, top))
    panel_x = width + margin * 2
    draw.text((panel_x, top), f"Annotations: {len(rows)} valid / {nonblank} rows", font=font, fill="white")
    draw.text((panel_x, top + 23), f"{errors} errors, {warning_count} warnings; see manifest", font=font, fill=(203, 213, 225))
    for index, row in enumerate(sidebar_rows):
        y = top + 62 + index * 42
        tag = "OUTSIDE" if row["outside_image"] else row["kind"].upper()
        draw.text((panel_x, y), f"L{row['line']} {row['category']}:{row['category_name']} [{tag}]",
                  font=font, fill=COLORS[row["display_color"]])
        coords = ",".join(f"{row[key]:g}" for key in ("x", "y", "width", "height"))
        draw.text((panel_x, y + 18), f"xywh={coords} | s={row['score']}", font=font, fill=(148, 163, 184))
    if len(rows) > 20:
        draw.text((panel_x, top + 62 + 20 * 42), "First 20 shown here; all valid rows in manifest", font=font, fill="white")
    footer = canvas.height - 58
    draw.text((margin, footer), "GREEN target | YELLOW ignored | PURPLE other | RED outside", font=font, fill="white")
    note = "PARTIAL: invalid rows skipped. See manifest." if errors else "Annotation review only; no predictions or model metrics."
    draw.text((margin, footer + 22), note, font=font, fill=(203, 213, 225))

    report = {
        "schema_version": 1, "scope": "single_pair_annotation_preview", "status": status,
        "source_kind": "synthetic_demo" if synthetic else "local_unverified_data",
        "split": split, "image": image_path.relative_to(root).as_posix(),
        "annotation": annotation_path.relative_to(root).as_posix(),
        "input_sha256": {
            "image": hashlib.sha256(image_bytes).hexdigest(),
            "annotation": hashlib.sha256(annotation_bytes).hexdigest(),
        },
        "decoder": {"name": "Pillow", "version": pillow_version},
        "image_size": [width, height], "image_offset_in_preview": [margin, top],
        "coordinate_policy": "raw_pixels_xywh_no_exif_transform_or_label_clipping",
        "display_policy": "integer_pixel_intersection_only; labels may overlap; sidebar first 20",
        "summary": {"nonblank_rows": nonblank, "valid_rows": len(rows),
                    "drawn_boxes": sum(r["display_bbox_xyxy"] is not None for r in rows),
                    "invalid_rows": nonblank - len(rows), "errors": errors, "warnings": warning_count},
        "rows": rows, "issues": issues,
        "not_checked": ["full_dataset_validation", "release_identity_and_terms",
                        "official_evaluator_equivalence", "model_metrics"],
        "artifacts": {"preview": "preview.png", "manifest": "manifest.json"},
    }
    # Exclusive directory creation protects prior outputs, including empty directories.
    output_dir.mkdir(parents=True, exist_ok=False)
    with (output_dir / "preview.png").open("xb") as handle:
        canvas.save(handle, format="PNG")
    with (output_dir / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    return report
