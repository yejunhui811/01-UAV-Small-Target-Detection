"""Render one VisDrone annotation pair or a clearly marked synthetic demo."""

import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uav_small_target.visdrone_preview import preview_annotations
from uav_small_target.visdrone_validation import SPLIT_DIRECTORIES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--root", type=Path, help="Raw root containing official labeled DET split directories")
    source.add_argument("--demo", action="store_true", help="Generate temporary synthetic fixtures; no dataset required")
    parser.add_argument("--split", choices=tuple(SPLIT_DIRECTORIES), default="train")
    parser.add_argument("--image-stem", help="Exact stem of a single matching image/TXT pair")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory outside raw root; existing directories refused")
    args = parser.parse_args(argv)
    if not args.demo and not args.image_stem:
        parser.error("--root requires --image-stem")
    if args.demo and (args.image_stem or args.split != "train"):
        parser.error("--demo uses its own train/synthetic-demo pair")
    try:
        if args.demo:
            from PIL import Image, ImageDraw
            with tempfile.TemporaryDirectory(prefix="uav-preview-demo-") as temporary:
                root = Path(temporary)
                images = root / "VisDrone2019-DET-train/images"
                annotations = root / "VisDrone2019-DET-train/annotations"
                images.mkdir(parents=True)
                annotations.mkdir()
                with Image.new("RGB", (640, 400), (226, 232, 240)) as image:
                    draw = ImageDraw.Draw(image)
                    draw.rectangle((0, 170, 639, 230), fill=(100, 116, 139))
                    for x, y in ((70, 80), (180, 180), (340, 290)):
                        draw.rectangle((x, y, x + 30, y + 20), fill=(51, 65, 85))
                    image.save(images / "synthetic-demo.png")
                (annotations / "synthetic-demo.txt").write_text(
                    "70,80,31,21,1,4,0,0\n180,180,31,21,0,4,0,0\n"
                    "340,290,31,21,1,11,0,0\n620,70,60,50,1,5,1,0\n"
                    "700,320,20,20,1,1,0,0\n", encoding="utf-8",
                )
                report = preview_annotations(root, "train", "synthetic-demo", args.output_dir, synthetic=True)
        else:
            report = preview_annotations(args.root, args.split, args.image_stem, args.output_dir)
    except (ImportError, ValueError, OSError) as exc:
        print(f"Preview could not complete: {exc}. Install requirements.txt if Pillow is missing.", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    print(f"{report['status']}: preview.png and manifest.json saved in {args.output_dir}", file=sys.stderr)
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
