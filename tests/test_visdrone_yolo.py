"""Synthetic tests of conversion geometry, provenance and failure protection."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))
from uav_small_target.visdrone_yolo import convert_dataset
from uav_small_target.visdrone_validation import SPLIT_DIRECTORIES
from uav_small_target.visdrone_annotations import AnnotationRowError, parse_annotation_row


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="uav-conversion-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "raw"
        self.output = self.root.parent / "derived"
        for split in ("train", "val"):
            self.sample(split)

    def sample(self, split="train", rows="10,20,20,10,1,4,0,0\n", stem="sample",
               format="PNG", **options):
        directory = self.root / SPLIT_DIRECTORIES[split]
        (directory / "images").mkdir(parents=True, exist_ok=True)
        (directory / "annotations").mkdir(exist_ok=True)
        image_path = directory / "images" / f"{stem}.{'jpg' if format == 'JPEG' else 'png'}"
        with Image.new("RGB", (100, 80), (20, 40, 60)) as image:
            image.save(image_path, format=format, **options)
        annotation = directory / "annotations" / f"{stem}.txt"
        annotation.write_text(rows, encoding="utf-8")
        return image_path, annotation

    def convert(self, **options):
        return convert_dataset(self.root, self.output, **options)

    def records(self):
        return [json.loads(line) for line in (self.output / "annotations.jsonl").read_text().splitlines()]

    def cli(self, *args, no_site=False):
        return subprocess.run([sys.executable, *(["-S"] if no_site else []), "-B",
                               str(REPOSITORY / "scripts/convert_visdrone_yolo.py"), *map(str, args)],
                              capture_output=True, text=True, cwd=self.temporary.name)

    def test_geometry_hashes_source_preservation_and_determinism(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = self.convert()
        self.assertEqual(report["status"], "converted")
        self.assertEqual(report, json.loads((self.output / "manifest.json").read_text()))
        label = (self.output / "labels/train/sample.txt").read_text().split()
        self.assertEqual(int(label[0]), 3)
        self.assertEqual(list(map(float, label[1:])), [0.2, 0.3125, 0.2, 0.125])
        for record in self.records():
            for key, path_key in (("image", "source_image"), ("annotation", "source_annotation")):
                source_bytes = before[self.root / record[path_key]]
                self.assertEqual(record["input_sha256"][key], hashlib.sha256(source_bytes).hexdigest())
            self.assertEqual((self.output / record["output_image"]).read_bytes(), before[self.root / record["source_image"]])
            label_bytes = (self.output / record["output_label"]).read_bytes()
            self.assertEqual(record["label_sha256"], hashlib.sha256(label_bytes).hexdigest())
        for name, expected in report["artifact_sha256"].items():
            self.assertEqual(hashlib.sha256((self.output / name).read_bytes()).hexdigest(), expected)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        second = Path(self.temporary.name) / "repeat"
        convert_dataset(self.root, second)
        self.assertEqual((second / "annotations.jsonl").read_bytes(), (self.output / "annotations.jsonl").read_bytes())
        self.assertEqual((second / "labels/train/sample.txt").read_bytes(), (self.output / "labels/train/sample.txt").read_bytes())

    def test_all_target_classes_and_excluded_rows_remain_in_sidecar(self):
        rows = "\n".join(f"1,2,3,4,1,{c},0,0" for c in range(1, 11))
        rows += "\n-100,0,5,5,0,4,1,2\n0,0,1,1,1,0,0,0\n0,0,1,1,1,11,0,0\n"
        self.sample(rows=rows)
        report = self.convert()
        labels = (self.output / "labels/train/sample.txt").read_text().splitlines()
        self.assertEqual([int(row.split()[0]) for row in labels], list(range(10)))
        record = self.records()[0]
        self.assertEqual(len(record["rows"]), 13)
        self.assertEqual([r["kind"] for r in record["rows"][-3:]], ["ignored", "ignored", "other"])
        self.assertTrue(all(r["yolo"] is None for r in record["rows"][-3:]))
        self.assertEqual(record["rows"][-3]["x"], -100)
        self.assertEqual(record["rows"][-3]["occlusion"], 2)
        self.assertEqual(report["splits"]["train"]["ignored_rows"], 2)
        self.assertEqual(report["splits"]["train"]["other_rows"], 1)

    def test_exact_boundary_fractional_and_tiny_extent_roundtrip(self):
        self.sample(rows="0,0,100,80,1,1,0,0\n1.5,2.5,0.000001,0.25,1,2,0,0,\n")
        self.convert()
        rows = [list(map(float, row.split()[1:])) for row in (self.output / "labels/train/sample.txt").read_text().splitlines()]
        self.assertEqual(rows[0], [0.5, 0.5, 1, 1])
        cx, cy, width, height = rows[1]
        self.assertAlmostEqual((cx - width / 2) * 100, 1.5)
        self.assertAlmostEqual((cy - height / 2) * 80, 2.5)
        self.assertAlmostEqual(width * 100, 0.000001)
        self.assertGreater(width, 0)

    def test_empty_and_only_ignored_labels_are_explicit_and_warn(self):
        self.sample(rows="\ufeff\n")
        self.sample("val", "0,0,1,1,0,4,0,0\n")
        report = self.convert()
        self.assertEqual(report["status"], "converted_with_warnings")
        for split in ("train", "val"):
            self.assertEqual((self.output / f"labels/{split}/sample.txt").read_bytes(), b"")
            self.assertEqual(report["splits"][split]["empty_label_images"], 1)

    def test_zero_area_exclusion_is_explicit_and_preserves_original_rows(self):
        self.sample(rows="10,20,20,10,1,4,0,0\n2,3,4,0,1,4,0,0\n2,3,0,4,0,0,0,0\n")
        with self.assertRaises(AnnotationRowError):
            parse_annotation_row("2,3,4,0,1,4,0,0")
        with self.assertRaises(ValueError):
            self.convert()
        report = self.convert(zero_area_policy="exclude")
        self.assertEqual(report["conversion_version"], "visdrone-yolo-v2")
        self.assertEqual(report["splits"]["train"]["source_rows"], 3)
        self.assertEqual(report["splits"]["train"]["target_rows"], 1)
        self.assertEqual(report["splits"]["train"]["excluded_zero_area_rows"], 2)
        rows = self.records()[0]["rows"]
        self.assertEqual(rows[1]["height"], 0)
        self.assertEqual(rows[2]["width"], 0)
        self.assertTrue(all(r["yolo"] is None and r["exclusion_reason"] == "zero_area_bbox" for r in rows[1:]))

    def test_zero_area_policy_never_allows_negative_or_other_core_errors(self):
        for row in ("2,3,-4,0,1,4,0,0", "2,3,4,0,1,12,0,0", "2,3,4,0,2,4,0,0",
                    "2,3,nan,0,1,4,0,0", "bad"):
            with self.subTest(row=row):
                self.sample(rows=row)
                with self.assertRaises(ValueError):
                    self.convert(zero_area_policy="exclude")
                self.assertFalse(self.output.exists())
        with self.assertRaises(ValueError):
            self.convert(zero_area_policy="silent")

    def test_invalid_rows_or_target_geometry_abort_without_publishing(self):
        for rows in ("bad", "0,0,1,1,1,12,0,0", "0,0,1,1,nan,1,0,0",
                     "0,0,0,1,1,1,0,0", "-1,0,2,2,1,1,0,0", "99,0,2,2,1,1,0,0",
                     "1e308,0,1e308,2,1,1,0,0", "5,1,1e-300,1,1,1,0,0",
                     "0,0,5e-324,1,1,1,0,0"):
            with self.subTest(rows=rows):
                # Bad val occurs after train has already been staged.
                self.sample("val", rows)
                with self.assertRaises(ValueError):
                    self.convert()
                self.assertFalse(self.output.exists())
                self.assertFalse(list(self.output.parent.glob(".uav-convert-*")))

    def test_bom_blank_lines_and_attributes_preserve_line_numbers(self):
        self.sample(rows="\ufeff\n10,20,20,10,1,4,-1,-1,\n")
        self.convert()
        record = self.records()[0]
        self.assertEqual(record["rows"][0]["line"], 2)
        self.assertEqual(record["rows"][0]["truncation"], -1)
        self.assertEqual(record["issues"][0]["code"], "unusual_attributes")

    def test_decoding_utf8_multiframe_truncation_and_pixel_limit_failures(self):
        for mode in ("corrupt", "utf8", "animated", "truncated", "pixel_limit"):
            with self.subTest(mode=mode):
                image, annotation = self.sample()
                if mode == "corrupt":
                    image.write_bytes(b"bad")
                elif mode == "utf8":
                    annotation.write_bytes(b"\xff")
                elif mode == "animated":
                    with Image.new("RGB", (100, 80), "red") as first, Image.new("RGB", (100, 80), "blue") as second:
                        first.save(image, save_all=True, append_images=[second])
                elif mode == "truncated":
                    with Image.new("RGB", (100, 80)) as im:
                        im.save(image, format="JPEG")
                    image.write_bytes(image.read_bytes()[:-2])
                with patch.object(Image, "MAX_IMAGE_PIXELS", 100 if mode == "pixel_limit" else Image.MAX_IMAGE_PIXELS):
                    with self.assertRaises(ValueError):
                        self.convert()
                self.assertFalse(self.output.exists())

    def test_nonidentity_exif_is_rejected_before_trainer_can_change_coordinates(self):
        image, _ = self.sample()
        image.unlink()
        exif = Image.Exif()
        exif[274] = 6
        self.sample(format="JPEG", exif=exif)
        with self.assertRaisesRegex(ValueError, "EXIF"):
            self.convert()
        self.assertFalse(self.output.exists())

    def test_missing_pairs_and_case_or_suffix_collisions(self):
        _, annotation = self.sample()
        annotation.unlink()
        with self.assertRaises(ValueError):
            self.convert()
        image, _ = self.sample()
        uppercase, _ = self.sample(stem="SAMPLE")
        original_iterdir = Path.iterdir

        def both_case_names(directory):
            # Case-insensitive macOS cannot create both names physically. Enumerate
            # both accessible names to exercise the portable collision guard.
            return iter((image, uppercase)) if directory == image.parent else original_iterdir(directory)

        with patch.object(Path, "iterdir", both_case_names), self.assertRaisesRegex(ValueError, "Ambiguous"):
            self.convert()
        for directory in ("images", "annotations"):
            for path in (self.root / SPLIT_DIRECTORIES["train"] / directory).iterdir():
                path.unlink()
        self.sample()
        self.sample(format="JPEG")
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            self.convert()

    def test_output_existing_raw_nested_symlink_and_concurrent_creation_are_protected(self):
        self.output.mkdir()
        marker = self.output / "user.txt"
        marker.write_text("preserve")
        with self.assertRaises(ValueError):
            self.convert()
        self.assertEqual(marker.read_text(), "preserve")
        for destination in (self.root / "derived", self.root.parent):
            with self.assertRaises(ValueError):
                convert_dataset(self.root, destination)
        alias = self.root.parent / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            convert_dataset(self.root, alias / "derived")
        dangling = self.root.parent / "dangling"
        dangling.symlink_to(self.root.parent / "missing-target", target_is_directory=True)
        with self.assertRaises(ValueError):
            convert_dataset(self.root, dangling)
        self.assertTrue(dangling.is_symlink())
        self.assertFalse((self.root.parent / "missing-target").exists())
        self.output = self.root.parent / "raced"
        original = Path.mkdir

        def concurrent_mkdir(path, *args, **kwargs):
            if path == self.output:
                original(path)
            return original(path, *args, **kwargs)

        with patch.object(Path, "mkdir", concurrent_mkdir), self.assertRaises(FileExistsError):
            self.convert()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_publication_io_failure_reports_failure_and_preserves_sources(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("uav_small_target.visdrone_yolo.shutil.move", side_effect=OSError("disk error")):
            result = None
            with self.assertRaises(OSError):
                result = self.convert()
            self.assertIsNone(result)
        self.assertTrue(self.output.is_dir())  # Reserved new output may be incomplete.
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertFalse(list(self.output.parent.glob(".uav-convert-*")))

    def test_split_mapping_and_yaml_have_no_download_hook(self):
        self.sample("test-dev")
        report = self.convert(splits=("test-dev", "val", "train"))
        self.assertEqual(report["split_mapping"], {"train": "train", "val": "val", "test-dev": "test"})
        self.assertTrue((self.output / "labels/test/sample.txt").is_file())
        yaml = (self.output / "dataset.yaml").read_text()
        self.assertIn("test: images/test\n", yaml)
        self.assertNotIn("download:", yaml)
        path = next(line.removeprefix("path: ") for line in yaml.splitlines() if line.startswith("path: "))
        self.assertEqual(json.loads(path), str(self.output))
        for number in range(10):
            self.assertIn(f"  {number}: ", yaml)
        for splits in (("train",), ("train", "val", "val"), ("train", "val", "test-challenge")):
            with self.assertRaises(ValueError):
                convert_dataset(self.root, self.root.parent / "unused", splits)

    def test_cli_demo_root_errors_and_missing_dependency(self):
        result = self.cli("--demo", "--output-dir", self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["source_kind"], "synthetic_demo")
        before = (self.output / "manifest.json").read_bytes()
        self.assertEqual(self.cli("--demo", "--output-dir", self.output).returncode, 2)
        self.assertEqual((self.output / "manifest.json").read_bytes(), before)
        result = self.cli("--root", self.root, "--output-dir", self.root.parent / "cli-output")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["source_kind"], "local_unverified_data")
        self.assertEqual(self.cli("--demo", "--splits", "train", "--output-dir", self.output).returncode, 2)
        self.assertEqual(self.cli("--help", no_site=True).returncode, 0)
        result = self.cli("--demo", "--output-dir", self.root.parent / "no-pillow", no_site=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Pillow", result.stderr)


if __name__ == "__main__":
    unittest.main()
