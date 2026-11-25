"""Run a local experiment independently of the chat, with durable logs/status."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from uav_small_target.yolo_experiment import load_config, now, write_json


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_worker(job):
    info = json.loads((job / "job.json").read_text())
    cfg = load_config(job / "config.toml")
    run = ROOT / "outputs" / cfg["experiment"]["id"]
    info.update(status="running", phase="training_and_evaluation", started_at=now())
    write_json(job / "job.json", info)
    with (job / "console.log").open("x") as log:
        child = subprocess.Popen([sys.executable, "-u", "-B", str(ROOT / "scripts/run_yolo_experiment.py"),
            "--config", str(job / "config.toml")], cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT)
        info["runner_pid"] = child.pid
        write_json(job / "job.json", info)
        code = child.wait()
    info.update(exit_code=code, finished_at=now())
    if code != 0:
        info.update(status="failed", phase="training_or_evaluation_failed")
    else:
        shutil.copyfile(job / "console.log", run / "console.log")
        info.update(status="completed", phase="completed")
        if info["export_aggregate"]:
            # Do not write public artifacts into a checkout changed by the user.
            unchanged = (git("branch", "--show-current") == info["branch"]
                         and git("rev-parse", "HEAD") == info["commit"] and not git("status", "--porcelain"))
            if not unchanged:
                info.update(status="completed_awaiting_export", phase="checkout_changed")
            else:
                with (job / "export.log").open("x") as log:
                    exported = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/summarize_yolo_run.py"),
                        "--run", str(run), "--figure"], cwd=ROOT, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT)
                info["export_exit_code"] = exported.returncode
                info.update(status="completed_awaiting_review" if exported.returncode == 0 else "completed_export_failed",
                            phase="aggregate_exported" if exported.returncode == 0 else "export_failed")
    write_json(job / "job.json", info)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--export", action="store_true", help="Export small aggregates after success; never commit/push/merge")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--status", help="Read job status by experiment ID")
    args = parser.parse_args(argv)
    if args.worker:
        job = args.worker.resolve()
        try:
            return run_worker(job)
        except BaseException as exc:
            info = json.loads((job / "job.json").read_text())
            info.update(status="worker_failed", finished_at=now(), error=f"{type(exc).__name__}: {exc}")
            write_json(job / "job.json", info)
            raise
    if args.status:
        if "/" in args.status or "\\" in args.status or args.status in (".", ".."):
            parser.error("Use an experiment ID, not a path")
        job = ROOT / "outputs/.jobs" / args.status
        print((job / "job.json").read_text())
        progress = ROOT / "outputs" / args.status / "progress.json"
        if progress.is_file():
            print(progress.read_text())
        return 0
    if args.config is None:
        parser.error("Choose --config or --status")
    cfg = load_config(args.config)
    experiment_id = cfg["experiment"]["id"]
    if (ROOT / "outputs" / experiment_id).exists():
        parser.error("Experiment run already exists; do not overwrite or start a duplicate")
    if git("status", "--porcelain"):
        parser.error("Commit validated code/configuration before starting a durable job")
    job = ROOT / "outputs/.jobs" / experiment_id
    job.mkdir(parents=True)  # Exclusive reservation also rejects a previous job.
    shutil.copyfile(args.config, job / "config.toml")
    info = {"experiment_id": experiment_id, "status": "launching", "phase": "launching", "created_at": now(),
            "branch": git("branch", "--show-current"), "commit": git("rev-parse", "HEAD"),
            "export_aggregate": args.export, "sleep_prevention": False}
    command = [sys.executable, "-u", "-B", str(Path(__file__).resolve()), "--worker", str(job)]
    caffeinate = shutil.which("caffeinate") if sys.platform == "darwin" else None
    if caffeinate:
        # Process-scoped idle/system sleep assertion; no persistent OS setting changes.
        command = [caffeinate, "-i", "-s", *command]
        info["sleep_prevention"] = True
    write_json(job / "job.json", info)
    with (job / "worker.log").open("x") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    # Separate launcher record avoids racing with worker updates to job.json.
    write_json(job / "launcher.json", {"supervisor_pid": process.pid, "launched_at": now()})
    print(f"Started durable local job {experiment_id}; supervisor PID {process.pid}")
    print(f"Status: outputs/.jobs/{experiment_id}/job.json; logs: console.log and worker.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
