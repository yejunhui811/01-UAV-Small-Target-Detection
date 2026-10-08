"""Local-only YOLO experiment configuration, provenance and evaluation helpers.

Heavy model dependencies are imported only by execution, not config validation.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import re
import shutil
import tomllib


VERSIONS = {"ultralytics": "8.4.174", "torch": "2.14.1", "torchvision": "0.29.1",
            "pycocotools": "2.0.11"}
WEIGHT_SHA256 = "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path, value):
    def scalar(value):
        if type(value).__module__.startswith("numpy") and getattr(value, "ndim", None) == 0:
            return value.item()
        raise TypeError(f"Unsupported JSON value: {type(value).__name__}")
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=scalar) + "\n",
                          encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat()


def load_config(path):
    with Path(path).open("rb") as handle:
        cfg = tomllib.load(handle)
    expected = {"experiment", "dataset", "model", "train", "evaluation"}
    if set(cfg) != expected:
        raise ValueError(f"Configuration requires exactly these sections: {sorted(expected)}")
    required = {
        "experiment": {"id", "kind", "hypothesis", "seed"},
        "dataset": {"root", "manifest_sha256", "train_images", "val_images"},
        "model": {"weights", "weights_sha256"},
        "train": {"device", "epochs", "imgsz", "batch", "workers", "optimizer", "lr0",
                  "momentum", "weight_decay", "mosaic", "close_mosaic"},
        "evaluation": {"conf", "nms_iou", "max_det", "timing_images", "warmup"},
    }
    for section, fields in required.items():
        if set(cfg[section]) != fields:
            raise ValueError(f"Unexpected or missing {section} keys")
    exp, data, train, evaluation = (cfg[k] for k in ("experiment", "dataset", "train", "evaluation"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", exp["id"]):
        raise ValueError("Experiment ID must be a portable lowercase name")
    if exp["kind"] not in ("smoke", "pilot", "baseline") or not exp["hypothesis"].strip():
        raise ValueError("Set smoke/pilot/baseline and a hypothesis")
    if not (train["device"] in ("cpu", "mps") or re.fullmatch(r"[0-9]+", train["device"])):
        raise ValueError("Choose an explicit cpu, mps or CUDA index")
    integers = [(exp, "seed", 0), (train, "epochs", 1), (train, "imgsz", 32),
                (train, "batch", 1), (train, "workers", 0), (train, "close_mosaic", 0),
                (data, "train_images", 0), (data, "val_images", 0),
                (evaluation, "max_det", 100), (evaluation, "timing_images", 1),
                (evaluation, "warmup", 1)]
    for section, key, minimum in integers:
        if type(section[key]) is not int or section[key] < minimum:
            raise ValueError(f"Invalid integer: {key}")
    if train["imgsz"] % 32 or train["optimizer"] != "SGD":
        raise ValueError("Use imgsz multiple of 32 and explicit SGD optimizer")
    for section, keys in ((train, ("lr0", "momentum", "weight_decay", "mosaic")),
                          (evaluation, ("conf", "nms_iou"))):
        for key in keys:
            value = section[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"Invalid probability/rate: {key}")
    if train["lr0"] <= 0 or evaluation["conf"] <= 0 or evaluation["nms_iou"] <= 0:
        raise ValueError("lr0, conf and nms_iou must be positive")
    if exp["kind"] in ("baseline", "pilot") and (data["train_images"] or data["val_images"]):
        raise ValueError("Pilot/baseline require full train and val; use smoke for subsets")
    for value in (data["manifest_sha256"], cfg["model"]["weights_sha256"]):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("Require explicit SHA-256 fingerprints")
    return cfg


def select_records(records, count, seed):
    if count > len(records):
        raise ValueError("Requested subset exceeds split size")
    if count:
        records = random.Random(seed).sample(records, count)
    return sorted(records, key=lambda row: row["output_image"])


def contained(root, name):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Dataset artifact escapes its root")
    return path


def prepare_dataset(cfg, root, run):
    """Hash check selected pairs, copy originals, keep framework cache in run only."""
    source = contained(root, cfg["dataset"]["root"])
    manifest_path = source / "manifest.json"
    if sha256(manifest_path) != cfg["dataset"]["manifest_sha256"]:
        raise ValueError("Dataset manifest fingerprint differs from configuration")
    manifest = json.loads(manifest_path.read_text())
    if manifest["conversion_version"] != "visdrone-yolo-v2":
        raise ValueError("Require audited VisDrone conversion v2")
    for name, digest in manifest["artifact_sha256"].items():
        if sha256(contained(source, name)) != digest:
            raise ValueError(f"Dataset artifact changed: {name}")
    splits = {"train": [], "val": []}
    with (source / "annotations.jsonl").open() as handle:
        for record in map(json.loads, handle):
            if record["output_split"] in splits:
                # Retain full GT rows for evaluation; training metadata stays compact.
                if record["output_split"] == "train":
                    record.pop("rows")
                splits[record["output_split"]].append(record)
    for split, rows in splits.items():
        if len(rows) != manifest["splits"][split]["images"]:
            raise ValueError("Dataset split count changed")
        splits[split] = select_records(rows, cfg["dataset"][f"{split}_images"], cfg["experiment"]["seed"])
    destination = run / "dataset"
    import yaml
    names = yaml.safe_load((source / "dataset.yaml").read_text())["names"]
    if len(names) != 10 or list(names) != list(range(10)):
        raise ValueError("Expected the 10 VisDrone target classes")
    for rows in splits.values():
        for record in rows:
            for key, expected in (("output_image", record["input_sha256"]["image"]),
                                  ("output_label", record["label_sha256"])):
                original = contained(source, record[key])
                if sha256(original) != expected:
                    raise ValueError(f"Dataset pair changed: {record[key]}")
                copied = contained(destination, record[key])
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, copied)
    (destination / "dataset.yaml").write_text(yaml.safe_dump({"path": str(destination),
        "train": "images/train", "val": "images/val", "names": names}, allow_unicode=True))
    write_json(run / "split-selection.json", {s: [r["output_image"] for r in rows] for s, rows in splits.items()})
    return splits, names


def coco_ground_truth(records, names):
    images, annotations = [], []
    for image_id, record in enumerate(records, 1):
        width, height = record["image_size"]
        images.append({"id": image_id, "file_name": Path(record["output_image"]).name,
                       "width": width, "height": height})
        for row in record["rows"]:
            if row["yolo"] is not None:
                annotations.append({"id": len(annotations) + 1, "image_id": image_id,
                    "category_id": row["category"], "bbox": [row[k] for k in ("x", "y", "width", "height")],
                    "area": row["width"] * row["height"], "iscrowd": 0})
    return {"info": {"description": "Converted target-only VisDrone; not official evaluation"},
            "images": images, "annotations": annotations,
            "categories": [{"id": i + 1, "name": name} for i, name in names.items()]}


def coco_metrics(ground_truth, predictions, max_det):
    """COCO protocol in original pixels; explicit maxDet and absent-area handling."""
    import numpy as np
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    gt = COCO()
    gt.dataset = ground_truth
    gt.createIndex()
    if predictions:
        detections = gt.loadRes(predictions)
    else:
        detections = COCO()
        detections.dataset = {**ground_truth, "annotations": []}
        detections.createIndex()
    evaluator = COCOeval(gt, detections, "bbox")
    evaluator.params.maxDets = [1, 10, max_det]
    evaluator.evaluate()
    evaluator.accumulate()
    precision = evaluator.eval["precision"]  # IoU, recall, class, area, maxDet
    def mean(values):
        values = values[values > -1]
        return float(np.mean(values)) if values.size else None
    return {"mAP50-95": mean(precision[:, :, :, 0, -1]),
            "mAP50": mean(precision[0, :, :, 0, -1]),
            "AP_small": mean(precision[:, :, :, 1, -1]),
            "AP_medium": mean(precision[:, :, :, 2, -1]),
            "AP_large": mean(precision[:, :, :, 3, -1]),
            "definition": {"evaluator": "pycocotools.COCOeval bbox", "area_coordinates": "original image pixels",
                "small_area_range_px2": [0, 1024], "iou_thresholds": [0.5, 0.95, 0.05],
                "recall_thresholds": "101 points", "max_detections": max_det,
                "ignored_regions": "excluded labels; no ignore suppression; not official VisDrone"}}


def box_iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    union = a[2] * a[3] + b[2] * b[3] - intersection
    return intersection / union if union > 0 else 0.0


def failure_summary(ground_truth, predictions, conf=0.25, iou=0.5):
    """Greedy same-class matching at fixed operating point, independent of AP."""
    gt_by_image, pred_by_image = {}, {}
    for row in ground_truth["annotations"]:
        gt_by_image.setdefault(row["image_id"], []).append(row)
    for row in predictions:
        if row["score"] >= conf:
            pred_by_image.setdefault(row["image_id"], []).append(row)
    cases, total_tp, total_fp, total_fn, small_total, small_missed = [], 0, 0, 0, 0, 0
    for image in ground_truth["images"]:
        gt = gt_by_image.get(image["id"], [])
        unmatched = set(range(len(gt)))
        tp, fp = 0, 0
        for pred in sorted(pred_by_image.get(image["id"], []), key=lambda x: x["score"], reverse=True):
            eligible = [(box_iou(pred["bbox"], gt[k]["bbox"]), k) for k in unmatched
                        if gt[k]["category_id"] == pred["category_id"]]
            overlap, match = max(eligible, default=(0, -1))
            if overlap >= iou:
                unmatched.remove(match)
                tp += 1
            else:
                fp += 1
        missed_small = sum(gt[k]["area"] <= 1024 for k in unmatched)
        small_total += sum(row["area"] <= 1024 for row in gt)
        small_missed += missed_small
        cases.append({"image_id": image["id"], "file_name": image["file_name"], "targets": len(gt),
                      "tp": tp, "fp": fp, "fn": len(unmatched), "missed_small": missed_small})
        total_tp += tp
        total_fp += fp
        total_fn += len(unmatched)
    return {"confidence": conf, "matching_iou": iou, "matching": "score-ordered same-class greedy one-to-one",
            "tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": total_tp / (total_tp + total_fp) if total_tp + total_fp else None,
            "recall": total_tp / (total_tp + total_fn) if total_tp + total_fn else None,
            "small_targets": small_total, "missed_small": small_missed,
            "worst_cases": sorted(cases, key=lambda row: row["fn"] + row["fp"], reverse=True)[:10],
            "not_checked": ["human cause attribution", "occlusion/density stratification", "official ignore rules"]}
