"""Validate the bootstrap structure without installing packages or running models."""

from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "AGENTS.md", "README.md", ".gitignore", "requirements.txt",
    "configs/README.md", "configs/experiment.example.toml", "src/README.md",
    "scripts/README.md", "scripts/validate_structure.py", "notebooks/README.md",
    "experiments/README.md", "experiments/template.md", "results/README.md",
    "results/figures/README.md", "results/tables/README.md", "docs/README.md",
    "docs/dataset.md", "docs/dependencies.md", "docs/evaluation.md",
    "docs/git-workflow.md", "assets/README.md",
)
IGNORED_PROBES = (
    "data/visdrone/sample.jpg", "datasets/sample.png", "weights/model.pt",
    "model.pt", "model.pth", "model.ckpt", "model.onnx", "model.safetensors",
    "outputs/predictions.csv", "runs/train/metrics.csv", "raw_images/image.jpg",
    "raw_videos/video.mp4", "clip.mov", "dataset.zip", ".env", ".env.local",
    "secrets/api-key.txt", "credentials/token.json", "private.pem",
    ".aws/credentials", "cache/item", ".cache/item", ".venv/bin/python",
    "src/__pycache__/module.pyc", "notebooks/.ipynb_checkpoints/test.ipynb",
    ".DS_Store", "temporary.tmp",
)
TRACKABLE_PROBES = REQUIRED_FILES + (
    "results/figures/reviewed.png", "results/tables/measured.csv",
    "assets/diagram.svg", ".env.example",
)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def main() -> int:
    errors = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing file: {relative}")

    # Check local paths only; no network access or remote URL verification.
    for relative in REQUIRED_FILES:
        document = ROOT / relative
        if document.suffix != ".md" or not document.is_file():
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = document.parent / unquote(parsed.path)
            if not resolved.exists():
                errors.append(f"Broken local link in {relative}: {target}")

    config_path = ROOT / "configs/experiment.example.toml"
    if config_path.is_file():
        try:
            with config_path.open("rb") as handle:
                config = tomllib.load(handle)
            if config.get("experiment", {}).get("status") != "planned":
                errors.append("Example configuration must remain planned")
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"Invalid TOML: {exc}")

    for expected, probes in ((True, IGNORED_PROBES), (False, TRACKABLE_PROBES)):
        for probe in probes:
            result = git("check-ignore", "--no-index", "-q", "--", probe)
            if result.returncode not in (0, 1):
                errors.append(f"git check-ignore failed: {result.stderr.strip()}")
            elif (result.returncode == 0) != expected:
                errors.append(f"Unexpected ignore policy for {probe}")

    # Reject forbidden files already staged/tracked, which .gitignore cannot remove.
    tracked = git("ls-files", "-z")
    if tracked.returncode:
        errors.append(f"git ls-files failed: {tracked.stderr.strip()}")
    else:
        for relative in filter(None, tracked.stdout.split("\0")):
            if git("check-ignore", "--no-index", "-q", "--", relative).returncode == 0:
                errors.append(f"Ignored file is staged/tracked: {relative}")
            path = ROOT / relative
            if path.is_file() and path.stat().st_size > 5 * 1024 * 1024:
                errors.append(f"Staged/tracked file exceeds review threshold (5 MiB): {relative}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: required files and directory placeholders")
    print("PASS: local Markdown link paths (remote URLs/anchors not checked)")
    print("PASS: TOML parsing and planned template status")
    print("PASS: dataset/weight/secret/cache/output ignore probes; docs/figures allowed")
    print("PASS: staged/tracked ignore policy and file size review threshold")
    print("No dataset download, model execution or benchmark performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
