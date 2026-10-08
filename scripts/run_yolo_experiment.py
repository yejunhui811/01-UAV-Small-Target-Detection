"""Train, evaluate, time and record a local YOLO experiment from pinned TOML."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uav_small_target.yolo_experiment import (
    VERSIONS, coco_ground_truth, coco_metrics, contained, failure_summary,
    load_config, now, prepare_dataset, progress_record, sha256, write_json, write_progress,
)


def execute(config_path, cfg, run):
    # Isolate settings and prevent auto-install/network logging during experiments.
    (run / "framework").mkdir()
    os.environ["YOLO_CONFIG_DIR"] = str(run / "framework")
    os.environ["YOLO_OFFLINE"] = "true"
    os.environ["YOLO_AUTOINSTALL"] = "false"
    os.environ["MPLCONFIGDIR"] = str(run / "matplotlib")
    for package, expected in VERSIONS.items():
        if importlib.metadata.version(package) != expected:
            raise ValueError(f"Require {package}=={expected}; install requirements-yolo.txt")
    import torch
    from ultralytics import YOLO, settings
    settings.update({"sync": False, "mlflow": False, "wandb": False, "comet": False,
                     "clearml": False, "dvc": False, "raytune": False})
    device = cfg["train"]["device"]
    if device == "mps" and not torch.backends.mps.is_available():
        raise ValueError("MPS unavailable; select CPU explicitly or use a supported GPU host")
    if device.isdigit() and (not torch.cuda.is_available() or int(device) >= torch.cuda.device_count()):
        raise ValueError("Requested CUDA device unavailable")
    torch.set_num_threads(4)
    weights = contained(ROOT, cfg["model"]["weights"])
    if sha256(weights) != cfg["model"]["weights_sha256"]:
        raise ValueError("Pretrained weight fingerprint mismatch")
    splits, names = prepare_dataset(cfg, ROOT, run)
    packages = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}
    write_json(run / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
        "machine": platform.machine(), "device": device, "packages": packages,
        "cuda_available": torch.cuda.is_available(), "mps_available": torch.backends.mps.is_available(),
        "cuda_version": torch.version.cuda, "cpu_threads": torch.get_num_threads(),
        "mps_fallback_env": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "unset")})
    train = cfg["train"]
    evaluation = cfg["evaluation"]
    shared = {"data": str(run / "dataset/dataset.yaml"), "device": device,
              "imgsz": train["imgsz"], "batch": train["batch"], "workers": train["workers"],
              "max_det": evaluation["max_det"], "plots": False, "project": str(run), "exist_ok": False}
    # Work in ignored run directory: third-party incidental files stay local.
    os.chdir(run)
    model = YOLO(str(weights))
    model.add_callback("on_train_start", lambda trainer: write_progress(run,
        progress_record(0, cfg["train"]["epochs"])))
    def record_epoch_progress(trainer):
        # final_eval also calls this hook with an extra logging step. It is not
        # another trained epoch, and best-checkpoint metrics are not epoch metrics.
        if trainer.validator.training:
            write_progress(run, progress_record(trainer.epoch + 1,
                cfg["train"]["epochs"], trainer.metrics))
    model.add_callback("on_fit_epoch_end", record_epoch_progress)
    model.train(**shared, name="train", epochs=train["epochs"], seed=cfg["experiment"]["seed"],
        deterministic=True, optimizer=train["optimizer"], lr0=train["lr0"], momentum=train["momentum"],
        weight_decay=train["weight_decay"], mosaic=train["mosaic"], close_mosaic=train["close_mosaic"],
        patience=0, amp=False, cache=False, save=True, pretrained=True, fraction=1.0,
        conf=evaluation["conf"], iou=evaluation["nms_iou"],
        hsv_h=0.015, hsv_s=0.7, hsv_v=0.4, degrees=0.0, translate=0.1, scale=0.5,
        shear=0.0, perspective=0.0, flipud=0.0, fliplr=0.5, mixup=0.0, cutmix=0.0)
    completed_epochs = model.trainer.epoch + 1
    if completed_epochs != train["epochs"]:
        raise ValueError(f"Training ended after {completed_epochs}/{train['epochs']} requested epochs")
    write_progress(run, {**progress_record(completed_epochs, train["epochs"]), "phase": "evaluation"})
    best = run / "train/weights/best.pt"
    if not best.is_file():
        raise ValueError("Training produced no best checkpoint")
    model = YOLO(str(best))
    val = model.val(**shared, name="validation", split="val", conf=evaluation["conf"],
                    iou=evaluation["nms_iou"], quantize=32, save_json=False)
    write_json(run / "ultralytics-validation.json", {
        "results_dict": {k: float(v) for k, v in val.results_dict.items()},
        "per_class": val.summary(), "speed_ms": val.speed,
        "precision_recall_definition": "Ultralytics mean P/R at smoothed mean-F1-selected confidence"})
    ground_truth = coco_ground_truth(splits["val"], names)
    write_json(run / "coco-ground-truth.json", ground_truth)
    images = [str(run / "dataset" / record["output_image"]) for record in splits["val"]]
    predictions = []
    options = {"device": device, "imgsz": train["imgsz"], "conf": evaluation["conf"],
               "iou": evaluation["nms_iou"], "max_det": evaluation["max_det"],
               "quantize": 32, "verbose": False, "save": False, "batch": 1}
    for image_id, result in enumerate(model.predict(source=images, stream=True, **options), 1):
        if Path(result.path).name != Path(images[image_id - 1]).name:
            raise ValueError("Prediction order differs from evaluation image order")
        boxes = result.boxes
        for box, cls, score in zip(boxes.xywh.cpu().tolist(), boxes.cls.cpu().tolist(), boxes.conf.cpu().tolist()):
            x, y, w, h = box
            predictions.append({"image_id": image_id, "category_id": int(cls) + 1,
                "bbox": [x - w / 2, y - h / 2, w, h], "score": score})
    write_json(run / "predictions.json", predictions)
    coco = coco_metrics(ground_truth, predictions, evaluation["max_det"])
    failures = failure_summary(ground_truth, predictions)
    write_json(run / "failure-analysis.json", failures)
    # Cache decoded arrays before timing; synchronization brackets full predict call.
    import cv2
    import numpy as np
    arrays = [cv2.imread(path) for path in images[:evaluation["timing_images"]]]
    if not arrays or any(array is None for array in arrays):
        raise ValueError("Timing input decoding failed")
    def synchronize():
        if device == "mps":
            torch.mps.synchronize()
        elif device.isdigit():
            torch.cuda.synchronize(int(device))
    # Fixed operating confidence for timing, independent of low-threshold AP pass.
    timing_options = {**options, "conf": 0.25}
    for i in range(evaluation["warmup"]):
        model.predict(source=arrays[i % len(arrays)], **timing_options)
    synchronize()
    seconds = []
    for array in arrays:
        synchronize()
        start = time.perf_counter()
        model.predict(source=array, **timing_options)
        synchronize()
        seconds.append(time.perf_counter() - start)
    timing = {"images": len(seconds), "warmup": evaluation["warmup"], "batch": 1,
        "latency_mean_ms": float(np.mean(seconds) * 1000), "latency_p50_ms": float(np.percentile(seconds, 50) * 1000),
        "latency_p95_ms": float(np.percentile(seconds, 95) * 1000), "FPS": len(seconds) / sum(seconds),
        "scope": "cached decoded BGR array -> preprocessing + inference + NMS + result construction; excludes disk/decode",
        "device_synchronization": "torch.mps/cuda synchronize before and after; CPU synchronous",
        "confidence": 0.25, "nms_iou": evaluation["nms_iou"], "max_det": evaluation["max_det"],
        "precision": "FP32", "sample": "first selected val images in lexical order", "seconds": seconds}
    results = {"kind": cfg["experiment"]["kind"], "trained_epochs": completed_epochs,
        "selected_images": {s: len(rows) for s, rows in splits.items()}, "coco": coco,
        "fixed_operating_point": {k: v for k, v in failures.items() if k != "worst_cases"},
        "timing": timing, "best_weights_sha256": sha256(best),
        "not_checked": ["official VisDrone evaluation", "convergence", "human failure attribution", "other devices"]}
    write_json(run / "metrics.json", results)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Parse configuration only; no model import or writes")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    if args.dry_run:
        print(json.dumps(cfg, indent=2))
        return 0
    run = ROOT / "outputs" / cfg["experiment"]["id"]
    if run.exists() or run.is_symlink():
        parser.error("Output already exists; choose a new experiment ID; never overwrite runs")
    run.mkdir(parents=True)
    config_path = args.config.resolve()
    shutil.copyfile(config_path, run / "config.toml")
    code = {p.relative_to(ROOT).as_posix(): sha256(p) for folder in ("src", "scripts")
            for p in (ROOT / folder).rglob("*.py")}
    git = lambda *a: subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()
    provenance = {"status": "running", "started_at": now(), "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")), "executed_source_sha256": code,
        "config_sha256": sha256(config_path), "command": [sys.executable, *sys.argv],
        "experiment": cfg["experiment"], "dataset_manifest_sha256": cfg["dataset"]["manifest_sha256"],
        "pretrained_weights_sha256": cfg["model"]["weights_sha256"]}
    write_json(run / "provenance.json", provenance)
    write_progress(run, {**progress_record(0, cfg["train"]["epochs"]), "phase": "preparing", "pid": os.getpid()})
    try:
        execute(config_path, cfg, run)
    except BaseException as exc:
        provenance.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                          finished_at=now(), error=f"{type(exc).__name__}: {exc}")
        write_json(run / "provenance.json", provenance)
        write_progress(run, {**json.loads((run / "progress.json").read_text()),
                             "status": provenance["status"], "error": provenance["error"], "updated_at": now()})
        raise
    provenance.update(status="completed", finished_at=now())
    write_json(run / "provenance.json", provenance)
    write_progress(run, {**progress_record(cfg["train"]["epochs"], cfg["train"]["epochs"]),
                         "status": "completed", "phase": "completed"})
    print(f"Completed: {run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
