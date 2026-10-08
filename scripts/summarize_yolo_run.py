"""Export reviewed aggregate tables/plots from a completed local YOLO run."""

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uav_small_target.yolo_experiment import load_config, sha256, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--figure", action="store_true")
    args = parser.parse_args(argv)
    run = args.run.resolve()
    if not run.is_relative_to((ROOT / "outputs").resolve()):
        parser.error("Use a local ignored outputs/ run")
    cfg = load_config(run / "config.toml")
    provenance = json.loads((run / "provenance.json").read_text())
    if provenance["status"] != "completed":
        parser.error("Only completed runs can produce measured result tables")
    metrics = json.loads((run / "metrics.json").read_text())
    failures = json.loads((run / "failure-analysis.json").read_text())
    environment = json.loads((run / "environment.json").read_text())
    packages = {name.lower(): version for name, version in environment["packages"].items()}
    experiment_id = cfg["experiment"]["id"]
    record_dir = ROOT / "experiments" / experiment_id
    table = ROOT / "results/tables" / f"{experiment_id}.csv"
    figure = ROOT / "results/figures" / f"{experiment_id}-ap.png"
    if record_dir.exists() or table.exists() or (args.figure and figure.exists()):
        parser.error("Public output already exists; review updates manually rather than overwrite")
    # Whitelist provenance fields; commands, paths, settings and full environment stay private.
    source_files = ("scripts/run_yolo_experiment.py", "src/uav_small_target/yolo_experiment.py")
    source_hashes = {name: provenance["executed_source_sha256"][name] for name in source_files}
    report = {"schema_version": 1, "experiment": cfg["experiment"], "status": provenance["status"],
        "started_at": provenance["started_at"], "finished_at": provenance["finished_at"],
        "code_base_commit": provenance["git_commit"], "executed_from_dirty_tree": provenance["git_dirty"],
        "executed_source_sha256": source_hashes, "configuration": cfg,
        "environment": {key: environment[key] for key in ("python", "platform", "machine", "device",
                                                         "cuda_available", "mps_available", "cpu_threads")},
        "package_versions": {name: packages[name.lower()] for name in
                            ("ultralytics", "torch", "torchvision", "pycocotools", "numpy", "Pillow")},
        "metrics": metrics, "failure_analysis": failures,
        "local_artifact_sha256": {name: sha256(run / name) for name in
            ("metrics.json", "provenance.json", "config.toml", "environment.json", "predictions.json",
             "failure-analysis.json", "ultralytics-validation.json", "split-selection.json")}}
    # Source mismatches are recorded explicitly: a later commit may include reporting fixes.
    report["executed_sources_match_current_files"] = all(sha256(ROOT / name) == digest
                                                       for name, digest in source_hashes.items())
    # Optional reviewed local cache audit contains counts/hashes only, not cache contents.
    if (run / "loader-audit.json").is_file():
        report["reviewed_loader_audit"] = json.loads((run / "loader-audit.json").read_text())
        report["local_artifact_sha256"]["loader-audit.json"] = sha256(run / "loader-audit.json")
    record_dir.mkdir()
    write_json(record_dir / "summary.json", report)
    values = {"experiment_id": experiment_id, "kind": metrics["kind"], "epochs": metrics["trained_epochs"],
        "train_images": metrics["selected_images"]["train"], "val_images": metrics["selected_images"]["val"],
        "imgsz": cfg["train"]["imgsz"], "mAP50_fraction": metrics["coco"]["mAP50"],
        "mAP50_95_fraction": metrics["coco"]["mAP50-95"], "AP_small_fraction": metrics["coco"]["AP_small"],
        "precision_conf025_iou050": metrics["fixed_operating_point"]["precision"],
        "recall_conf025_iou050": metrics["fixed_operating_point"]["recall"],
        "FPS_cached_array": metrics["timing"]["FPS"], "latency_mean_ms": metrics["timing"]["latency_mean_ms"],
        "latency_p95_ms": metrics["timing"]["latency_p95_ms"]}
    with table.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=values.keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerow({k: "not measured" if v is None else v for k, v in values.items()})
    if args.figure:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        areas = ("AP_small", "AP_medium", "AP_large")
        scores = [metrics["coco"][key] for key in areas]
        if any(score is None for score in scores):
            parser.error("Area group has no measured AP; omit --figure")
        fig, ax = plt.subplots(figsize=(6.4, 4.2), layout="constrained")
        bars = ax.bar(["Small", "Medium", "Large"], [score * 100 for score in scores],
                      color=["#24577a", "#478caf", "#81bacb"])
        ax.bar_label(bars, fmt="%.2f%%", padding=3)
        ax.set_ylabel("COCO AP50-95 (%)")
        ax.set_ylim(0, max(1, max(scores) * 100 * 1.3))
        ax.set_title(f"YOLO11n: {metrics['trained_epochs']} epoch {metrics['kind']} / imgsz {cfg['train']['imgsz']}")
        ax.text(0.5, -0.2, "Original pixel area; target-only labels; maxDet 500; not official VisDrone",
                transform=ax.transAxes, ha="center", fontsize=8)
        fig.savefig(figure, dpi=160)
        plt.close(fig)
    print(f"Exported summary: {record_dir / 'summary.json'}")
    print(f"Exported table: {table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
