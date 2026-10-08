"""Synthetic preview tests: geometry, annotation semantics and source protection."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))
from uav_small_target.visdrone_preview import COLORS, preview_annotations
from uav_small_target.visdrone_validation import validate_dataset


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="uav-preview-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "raw"
        self.images = self.root / "VisDrone2019-DET-train/images"
        self.annotations = self.root / "VisDrone2019-DET-train/annotations"
        self.images.mkdir(parents=True)
        self.annotations.mkdir()
        self.output = Path(self.temporary.name) / "preview"

    def sample(self, rows="20,30,10,10,1,4,0,0\n", *, format="PNG", size=(320, 200), **options):
        image = self.images / f"sample.{'jpg' if format == 'JPEG' else 'png'}"
        annotation = self.annotations / "sample.txt"
        with Image.new("RGB", size, (220, 230, 240)) as im:
            im.save(image, format=format, **options)
        annotation.write_text(rows, encoding="utf-8")
        return image, annotation

    def preview(self, **kwargs):
        return preview_annotations(self.root, "train", "sample", self.output, **kwargs)

    def cli(self, *extra, no_site=False):
        return subprocess.run(
            [sys.executable, *(["-S"] if no_site else []), "-B",
             str(REPOSITORY / "scripts/preview_visdrone.py"), *map(str, extra)],
            capture_output=True, text=True, cwd=self.temporary.name,
        )

    def real_args(self):
        return ("--root", self.root, "--image-stem", "sample", "--output-dir", self.output)

    def test_render_pixels_source_hashes_and_repeatability(self):
        image, annotation = self.sample()
        before = {p: p.read_bytes() for p in (image, annotation)}
        report = self.preview()
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["input_sha256"],
                         {k: hashlib.sha256(before[p]).hexdigest() for k, p in (("image", image), ("annotation", annotation))})
        self.assertEqual(report, json.loads((self.output / "manifest.json").read_text()))
        with Image.open(self.output / "preview.png") as rendered:
            ox, oy = report["image_offset_in_preview"]
            self.assertEqual(rendered.getpixel((ox + 20, oy + 30)), COLORS["target"])
            self.assertEqual(rendered.getpixel((ox + 29, oy + 39)), COLORS["target"])
            self.assertEqual(rendered.getpixel((ox + 30, oy + 39)), (220, 230, 240))
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        second = Path(self.temporary.name) / "repeat"
        self.assertEqual(preview_annotations(self.root, "train", "sample", second), report)
        self.assertEqual((second / "preview.png").read_bytes(), (self.output / "preview.png").read_bytes())

    def test_class_mapping_and_ignored_other_semantics(self):
        self.sample("\n".join(f"20,30,10,10,{0 if c == 0 else 1},{c},0,0" for c in range(12))
                    + "\n20,30,10,10,0,4,0,0\n")
        rows = self.preview()["rows"]
        self.assertEqual([r["category_name"] for r in rows[:12]], [
            "ignored regions", "pedestrian", "people", "bicycle", "car", "van",
            "truck", "tricycle", "awning-tricycle", "bus", "motor", "others",
        ])
        self.assertEqual(rows[0]["kind"], "ignored")
        self.assertEqual(rows[11]["kind"], "other")
        self.assertEqual(rows[12]["kind"], "ignored")
        self.assertTrue(all(r["kind"] == "target" for r in rows[1:11]))

    def test_exact_edges_fractional_and_one_pixel_geometry(self):
        self.sample("0,0,320,200,1,4,0,0\n20.5,30.5,0.2,0.2,1,1,0,0\n319,199,1,1,1,4,0,0\n")
        report = self.preview()
        self.assertEqual(report["status"], "ready")
        self.assertEqual([r["display_bbox_xyxy"] for r in report["rows"]],
                         [[0, 0, 319, 199], [20, 30, 20, 30], [319, 199, 319, 199]])

    def test_single_pixel_outline_does_not_spill_into_neighbors(self):
        self.sample("20.5,30.5,0.2,0.2,1,1,0,0\n")
        report = self.preview()
        ox, oy = report["image_offset_in_preview"]
        with Image.open(self.output / "preview.png") as rendered:
            self.assertEqual(rendered.getpixel((ox + 20, oy + 30)), COLORS["target"])
            for x, y in ((19, 30), (21, 30), (20, 31)):
                self.assertEqual(rendered.getpixel((ox + x, oy + y)), (220, 230, 240))

    def test_outside_boxes_preserve_raw_coordinates_and_offscreen_rows(self):
        self.sample("-5,20,10,10,1,4,1,0\n315,30,10,10,1,4,1,0\n"
                    "400,10,20,20,1,1,0,0\n1e308,10,1e308,20,1,1,0,0\n")
        report = self.preview()
        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["rows"][0]["x"], -5)
        self.assertEqual([r["display_bbox_xyxy"] for r in report["rows"]],
                         [[0, 20, 4, 29], [315, 30, 319, 39], None, None])
        self.assertEqual(report["summary"]["drawn_boxes"], 2)
        self.assertTrue(all(r["display_color"] == "outside" for r in report["rows"]))

    def test_bad_rows_are_partial_and_share_validator_core_errors(self):
        self.sample("\ufeff\n0,0,0,1,2,12,0,0\nwrong\n20,30,10,10,1,4,-1,-1,\n")
        report = self.preview()
        validation = validate_dataset(self.root, ("train",))
        core = [(i["code"], i["line"]) for i in validation["issues"] if i["severity"] == "error"]
        self.assertEqual([(i["code"], i["line"]) for i in report["issues"] if i["severity"] == "error"], core)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["summary"]["invalid_rows"], 2)
        self.assertEqual(report["rows"][0]["line"], 4)
        self.assertTrue((self.output / "preview.png").is_file())

    def test_empty_labels_keep_image_and_warn(self):
        self.sample("\n")
        report = self.preview()
        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["rows"], [])
        self.assertEqual(report["issues"][0]["code"], "empty_annotation")
        with Image.open(self.output / "preview.png") as rendered:
            ox, oy = report["image_offset_in_preview"]
            self.assertEqual(rendered.getpixel((ox + 20, oy + 30)), (220, 230, 240))

    def test_decode_and_utf8_failures_create_no_output(self):
        for corruption in ("image", "annotation", "jpeg", "animated"):
            with self.subTest(corruption=corruption):
                image, annotation = self.sample()
                if corruption == "image":
                    image.write_bytes(b"corrupt")
                elif corruption == "annotation":
                    annotation.write_bytes(b"\xff")
                elif corruption == "jpeg":
                    with Image.new("RGB", (320, 200)) as im:
                        im.save(image, format="JPEG")
                    image.write_bytes(image.read_bytes()[:-2])
                else:
                    with Image.new("RGB", (320, 200), "black") as first, Image.new("RGB", (320, 200), "white") as second:
                        first.save(image, format="PNG", save_all=True, append_images=[second])
                with self.assertRaises(ValueError):
                    self.preview()
                self.assertFalse(self.output.exists())

    def test_exif_orientation_uses_unrotated_extent(self):
        exif = Image.Exif()
        exif[274] = 6
        self.sample("319,0,1,200,1,4,0,0\n", format="JPEG", exif=exif)
        report = self.preview()
        self.assertEqual(report["image_size"], [320, 200])
        self.assertEqual(report["status"], "ready")

    def test_existing_and_raw_output_directories_are_protected(self):
        self.sample()
        self.output.mkdir()
        marker = self.output / "user.txt"
        marker.write_text("preserve")
        with self.assertRaises(ValueError):
            self.preview()
        self.assertEqual(list(self.output.iterdir()), [marker])
        with self.assertRaises(ValueError):
            preview_annotations(self.root, "train", "sample", self.root / "preview")
        alias = Path(self.temporary.name) / "raw-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            preview_annotations(self.root, "train", "sample", alias / "preview")

    def test_missing_ambiguous_pair_and_unsafe_stem_rejected(self):
        image, _ = self.sample()
        for stem in ("", "..", "../sample", "dir\\sample"):
            with self.subTest(stem=stem), self.assertRaises(ValueError):
                preview_annotations(self.root, "train", stem, self.output)
        with self.assertRaises(ValueError):
            preview_annotations(self.root, "test-challenge", "sample", self.output)
        image.unlink()
        with self.assertRaises(ValueError):
            self.preview()
        self.sample()
        self.sample(format="JPEG")
        with self.assertRaises(ValueError):
            self.preview()
        self.assertFalse(self.output.exists())

    def test_cli_demo_outputs_and_no_overwrite(self):
        result = self.cli("--demo", "--output-dir", self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["source_kind"], "synthetic_demo")
        self.assertEqual(report["summary"]["valid_rows"], 5)
        self.assertEqual(report["summary"]["drawn_boxes"], 4)
        self.assertEqual({p.name for p in self.output.iterdir()}, {"preview.png", "manifest.json"})
        before = (self.output / "preview.png").read_bytes()
        self.assertEqual(self.cli("--demo", "--output-dir", self.output).returncode, 2)
        self.assertEqual((self.output / "preview.png").read_bytes(), before)

    def test_cli_partial_and_usage_dependency_errors(self):
        self.sample("bad row\n")
        result = self.cli(*self.real_args())
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "partial")
        self.assertEqual(self.cli("--root", self.root, "--output-dir", self.output).returncode, 2)
        self.assertEqual(self.cli("--demo", "--image-stem", "x", "--output-dir", self.output).returncode, 2)
        self.assertEqual(self.cli("--help", no_site=True).returncode, 0)
        result = self.cli("--demo", "--output-dir", self.output / "new", no_site=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Pillow", result.stderr)

    def test_display_precision_loss_skips_box_without_crashing(self):
        self.sample("5,10,1e-300,1,1,1,0,0\n")
        report = self.preview()
        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["rows"][0]["width"], 1e-300)
        self.assertIsNone(report["rows"][0]["display_bbox_xyxy"])
        self.assertEqual(report["issues"][0]["code"], "bbox_display_precision")

    def test_sidebar_limit_does_not_discard_annotations(self):
        self.sample("20,30,10,10,1,4,0,0\n" * 21)
        report = self.preview()
        self.assertEqual(len(report["rows"]), 21)
        self.assertEqual(report["summary"]["drawn_boxes"], 21)


if __name__ == "__main__":
    unittest.main()
