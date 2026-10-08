"""Image decoding and geometry checks using temporary synthetic fixtures only."""

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

from PIL import Image, __version__ as pillow_version

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))
from uav_small_target.visdrone_validation import validate_dataset


class VisDroneImageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="uav-image-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "raw"
        self.images = self.root / "VisDrone2019-DET-train/images"
        self.annotations = self.root / "VisDrone2019-DET-train/annotations"
        self.images.mkdir(parents=True)
        self.annotations.mkdir()

    def sample(self, rows="0,0,6,4,1,1,0,0\n", name="sample", format="PNG", **save_options):
        path = self.images / f"{name}.{'jpg' if format == 'JPEG' else 'png'}"
        with Image.new("RGB", (6, 4), (20, 40, 60)) as image:
            image.save(path, format=format, **save_options)
        annotation = self.annotations / f"{name}.txt"
        annotation.write_text(rows)
        return path, annotation

    def report(self, **kwargs):
        return validate_dataset(self.root, ("train",), check_images=True, **kwargs)

    def codes(self, report):
        return {item["code"] for item in report["issues"]}

    def cli(self, *extra, no_site=False):
        return subprocess.run(
            [sys.executable, *(["-S"] if no_site else []), "-B",
             str(REPOSITORY / "scripts/validate_visdrone.py"), "--root", str(self.root),
             "--splits", "train", *map(str, extra)],
            capture_output=True, text=True, cwd=self.temporary.name,
        )

    def test_png_jpeg_decode_and_exact_edges_preserve_bytes(self):
        paths = [self.sample(), self.sample(name="jpeg", format="JPEG")]
        before = {p: p.read_bytes() for pair in paths for p in pair}
        report = self.report()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["decoder"], {"name": "Pillow", "version": pillow_version})
        self.assertEqual(report["splits"]["train"]["image_decoding"],
                         {"attempted": 2, "decoded": 2, "failed": 0})
        self.assertEqual(report["splits"]["train"]["bbox_boundaries"],
                         {"checked": 2, "skipped": 0, "outside": 0})
        self.assertNotIn("full_image_decoding", report["not_checked"])
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_bbox_overflow_and_negative_origins_warn_without_clipping(self):
        _, annotation = self.sample(
            "5,0,2,1,1,1,0,0\n0,3,1,2,1,1,0,0\n"
            "-1,0,2,1,1,1,1,0\n0,-1,1,2,0,0,1,0\n"
            "7,5,1,1,1,11,0,0\n0.5,0.5,5.5,3.5,1,1,0,0\n"
        )
        before = annotation.read_bytes()
        report = self.report()
        outside = [i for i in report["issues"] if i["code"] == "bbox_outside_image"]
        self.assertEqual(report["status"], "warning")
        self.assertEqual([i["line"] for i in outside], [1, 2, 3, 4, 5])
        self.assertTrue(all(i["severity"] == "warning" for i in outside))
        self.assertEqual(report["splits"]["train"]["bbox_boundaries"],
                         {"checked": 6, "skipped": 0, "outside": 5})
        self.assertEqual(annotation.read_bytes(), before)

    def test_zero_bytes_and_unidentified_image_fail(self):
        for payload in (b"", b"not an image"):
            with self.subTest(payload=payload):
                image, _ = self.sample()
                image.write_bytes(payload)
                report = self.report()
                self.assertEqual(report["status"], "failed")
                self.assertIn("image_decode_error", self.codes(report))
                self.assertEqual(report["bbox_check"], "partial")
                self.assertEqual(report["splits"]["train"]["bbox_boundaries"]["skipped"], 1)

    def test_valid_png_container_with_broken_pixel_stream_fails_load(self):
        image, _ = self.sample()
        data = image.read_bytes()
        start = data.index(b"IDAT")
        length = struct.unpack(">I", data[start - 4:start])[0]
        payload = b"broken compressed pixels"
        replacement = (struct.pack(">I", len(payload)) + b"IDAT" + payload
                       + struct.pack(">I", zlib.crc32(b"IDAT" + payload)))
        image.write_bytes(data[:start - 4] + replacement + data[start + 4 + length + 4:])
        with Image.open(image) as opened:
            opened.verify()  # Header/container validity alone is insufficient.
        self.assertIn("image_decode_error", self.codes(self.report()))

    def test_truncated_jpeg_fails_and_other_images_still_checked(self):
        image, _ = self.sample(format="JPEG")
        image.write_bytes(image.read_bytes()[:-2])
        self.sample(name="good")
        report = self.report()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["splits"]["train"]["image_decoding"],
                         {"attempted": 2, "decoded": 1, "failed": 1})
        self.assertEqual(report["splits"]["train"]["bbox_boundaries"],
                         {"checked": 1, "skipped": 1, "outside": 0})

    def test_png_checksum_corruption_fails_verify(self):
        image, _ = self.sample()
        data = bytearray(image.read_bytes())
        start = data.index(b"IDAT")
        length = struct.unpack(">I", data[start - 4:start])[0]
        data[start + 4 + length] ^= 1
        image.write_bytes(data)
        self.assertIn("image_decode_error", self.codes(self.report()))

    def test_exif_orientation_does_not_change_raw_coordinate_extent(self):
        exif = Image.Exif()
        exif[274] = 6
        self.sample("5,0,1,4,1,1,0,0\n", format="JPEG", exif=exif)
        self.assertEqual(self.report()["status"], "passed")

    def test_ambiguous_or_missing_image_skips_bbox_review(self):
        self.sample()
        self.sample(format="JPEG")
        (self.annotations / "missing.txt").write_text("0,0,1,1,1,1,0,0\n")
        report = self.report()
        self.assertEqual(report["bbox_check"], "partial")
        self.assertEqual(report["splits"]["train"]["bbox_boundaries"],
                         {"checked": 0, "skipped": 2, "outside": 0})

    def test_pillow_pixel_limit_warning_and_error_are_reported(self):
        self.sample()
        for limit in (20, 5):  # Image is 24 pixels: warning, then error.
            with self.subTest(limit=limit), patch.object(Image, "MAX_IMAGE_PIXELS", limit):
                report = self.report()
                self.assertEqual(report["status"], "failed")
                self.assertIn("image_decode_error", self.codes(report))

    def test_multiframe_png_is_rejected(self):
        image, _ = self.sample()
        with Image.new("RGB", (6, 4), "black") as first, Image.new("RGB", (6, 4), "white") as second:
            first.save(image, save_all=True, append_images=[second], format="PNG")
        report = self.report()
        self.assertIn("image_decode_error", self.codes(report))

    def test_cli_flag_json_exit_codes_and_combined_duplicate_check(self):
        self.sample()
        result = self.cli("--check-images", "--check-duplicates")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["image_check"], "pillow_verify_and_load")
        self.sample("6,0,1,1,1,1,0,0\n")
        self.assertEqual(self.cli("--check-images").returncode, 0)  # Review warning.
        image, _ = self.sample()
        image.write_bytes(b"broken")
        self.assertEqual(self.cli("--check-images").returncode, 1)

    def test_missing_pillow_only_blocks_requested_image_check(self):
        self.sample()
        self.assertEqual(self.cli(no_site=True).returncode, 0)
        result = self.cli("--check-images", no_site=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires Pillow", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
