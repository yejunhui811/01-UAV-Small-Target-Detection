"""Convert prepared local VisDrone DET splits, or run a synthetic-only demo."""

import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uav_small_target.visdrone_yolo import convert_dataset
from uav_small_target.visdrone_validation import SPLIT_DIRECTORIES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--root", type=Path, help="Prepared raw root; no download performed")
    source.add_argument("--demo", action="store_true", help="Use temporary synthetic train/val pairs")
    parser.add_argument("--splits", nargs="+", choices=tuple(SPLIT_DIRECTORIES), default=["train", "val"])
    parser.add_argument("--output-dir", required=True, type=Path, help="New directory separate from raw root")
    parser.add_argument("--zero-area-policy", choices=("reject", "exclude"), default="reject",
                        help="v2: explicitly exclude zero-area rows with full provenance; all other invalid rows still fail")
    args = parser.parse_args(argv)
    if args.demo and args.splits != ["train", "val"]:
        parser.error("--demo uses train and val only")
    try:
        if args.demo:
            from PIL import Image
            with tempfile.TemporaryDirectory(prefix="uav-yolo-demo-") as temporary:
                root = Path(temporary)
                for split, size in (("train", (100, 80)), ("val", (120, 90))):
                    directory = root / SPLIT_DIRECTORIES[split]
                    (directory / "images").mkdir(parents=True)
                    (directory / "annotations").mkdir()
                    with Image.new("RGB", size, (40, 80, 120)) as image:
                        image.save(directory / "images/synthetic.png")
                    (directory / "annotations/synthetic.txt").write_text(
                        "10,20,20,10,1,4,0,0\n0,0,5,5,0,1,0,0\n"
                        "30,30,10,10,1,11,0,0\n", encoding="utf-8")
                report = convert_dataset(root, args.output_dir, synthetic=True, zero_area_policy=args.zero_area_policy)
        else:
            report = convert_dataset(args.root, args.output_dir, args.splits, zero_area_policy=args.zero_area_policy)
    except (ImportError, OSError, ValueError) as exc:
        print(f"Conversion could not complete: {exc}. Check inputs and install requirements.txt if Pillow is missing.", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    print(f"{report['status']}: saved in {args.output_dir}; no training or evaluation performed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
