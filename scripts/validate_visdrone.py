"""CLI for read-only VisDrone DET pairing and annotation checks."""

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uav_small_target.visdrone_validation import SPLIT_DIRECTORIES, validate_dataset


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Directory containing VisDrone2019-DET-{train,val,test-dev}")
    parser.add_argument("--splits", nargs="+", choices=tuple(SPLIT_DIRECTORIES), default=["train", "val"])
    parser.add_argument("--check-duplicates", action="store_true", help="Hash image bytes and flag exact duplicates; adds disk I/O")
    parser.add_argument("--report", type=Path, help="Also save JSON outside the dataset; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        if args.report and args.report.resolve().is_relative_to(args.root.resolve()):
            raise ValueError("Report must be outside the dataset root to preserve raw files")
        report = validate_dataset(args.root, tuple(args.splits), check_duplicates=args.check_duplicates)
        text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as handle:
                handle.write(text)
    except (ValueError, OSError) as exc:
        print(f"Validation could not run/save report: {exc}", file=sys.stderr)
        return 2
    print(text, end="")
    print(
        f"{report['status']}: {report['summary']['errors']} errors, "
        f"{report['summary']['warnings']} warnings. See not_checked for limits.",
        file=sys.stderr,
    )
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
