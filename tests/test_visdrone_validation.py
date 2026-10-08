"""Synthetic fixtures only: no VisDrone files, downloads or research results."""

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))
from uav_small_target.visdrone_validation import validate_dataset


def png_bytes(color=0):
    """Generate a small real PNG without an image dependency."""
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + bytes([color]) * 6) * 2))
        + chunk(b"IEND", b"")
    )


class VisDroneValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="uav-validator-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "raw"
        self.root.mkdir()

    def sample(self, text="0,0,1,1,1,1,0,0\n", split="train", name="sample", color=0):
        directory = self.root / f"VisDrone2019-DET-{split}"
        (directory / "images").mkdir(parents=True, exist_ok=True)
        (directory / "annotations").mkdir(parents=True, exist_ok=True)
        image = directory / "images" / f"{name}.png"
        annotation = directory / "annotations" / f"{name}.txt"
        image.write_bytes(png_bytes(color))
        annotation.write_text(text)
        return image, annotation

    def report(self, **kwargs):
        return validate_dataset(self.root, ("train",), **kwargs)

    def codes(self, report):
        return {item["code"] for item in report["issues"]}

    def cli(self, *extra):
        return subprocess.run(
            [sys.executable, "-B", str(REPOSITORY / "scripts/validate_visdrone.py"),
             "--root", str(self.root), "--splits", "train", *map(str, extra)],
            capture_output=True, text=True, cwd=self.temporary.name,
        )

    def test_valid_pairs_preserve_target_and_ignored_metadata(self):
        image, annotation = self.sample(
            "0,0,1,1,1,1,0,0\n0,0,1,1,0,2,0,0\n"
            "0,0,2,2,0,0,0,0\n0,0,1,1,1,11,0,0\n"
        )
        original = (image.read_bytes(), annotation.read_bytes())
        report = self.report()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["splits"]["train"]["matched_pairs"], 1)
        self.assertEqual(report["splits"]["train"]["target_rows"], 1)
        self.assertEqual(report["splits"]["train"]["ignored_or_other_rows"], 3)
        self.assertEqual(original, (image.read_bytes(), annotation.read_bytes()))

    def test_bom_whitespace_and_one_trailing_comma(self):
        self.sample("\ufeff 0, 0, 1, 1, 1, 10, 0, 2,\n\n")
        self.assertEqual(self.report()["status"], "passed")

    def test_all_original_categories_remain_distinct(self):
        rows = [f"0,0,1,1,{0 if category in (0, 11) else 1},{category},0,0" for category in range(12)]
        self.sample("\n".join(rows) + "\n")
        summary = self.report()["splits"]["train"]
        self.assertEqual(summary["target_rows"], 10)
        self.assertEqual(summary["ignored_or_other_rows"], 2)
        self.assertEqual(summary["original_category_counts"], {str(category): 1 for category in range(12)})

    def test_labeled_test_dev_can_be_selected_alone(self):
        self.sample(split="test-dev")
        report = validate_dataset(self.root, ("test-dev",))
        self.assertEqual(report["status"], "passed")
        self.assertEqual(set(report["splits"]), {"test-dev"})

    def test_bad_rows_are_reported_with_original_line_numbers(self):
        cases = {
            "1,2,3": "field_count", "0,0,bad,1,1,1,0,0": "non_numeric",
            "0,0,nan,1,1,1,0,0": "non_finite", "0,0,inf,1,1,1,0,0": "non_finite",
            "0,0,1,1,1,1.5,0,0": "non_integer_metadata",
            "0,0,1,1,2,1,0,0": "invalid_score",
            "0,0,1,1,1,12,0,0": "invalid_category",
            "0,0,0,1,1,1,0,0": "invalid_bbox_size",
            "0,0,1,1,1,1,0,0,,": "field_count",
        }
        for row, code in cases.items():
            with self.subTest(row=row):
                self.sample("\n" + row + "\n0,0,1,1,1,1,0,0\n")
                report = self.report()
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["issues"][0]["code"], code)
                self.assertEqual(report["issues"][0]["line"], 2)
                self.assertEqual(report["splits"]["train"]["target_rows"], 1)

    def test_missing_counterparts(self):
        image, _ = self.sample()
        image.unlink()
        self.assertIn("missing_image", self.codes(self.report()))
        self.sample()
        (image.parent / "unmatched.png").write_bytes(png_bytes(1))
        self.assertIn("missing_annotation", self.codes(self.report()))

    def test_missing_and_empty_directories_fail(self):
        report = self.report()
        self.assertEqual(report["status"], "failed")
        self.assertIn("missing_directory", self.codes(report))
        image, annotation = self.sample()
        image.unlink()
        annotation.unlink()
        self.assertIn("empty_images", self.codes(self.report()))
        self.assertIn("empty_annotations", self.codes(self.report()))

    def test_stem_collision_is_not_counted_as_unique_pair(self):
        image, _ = self.sample()
        (image.parent / "sample.jpg").write_bytes(b"synthetic metadata-only placeholder")
        report = self.report()
        self.assertIn("ambiguous_stem", self.codes(report))
        self.assertEqual(report["splits"]["train"]["matched_pairs"], 0)

    def test_zero_byte_image_and_unreadable_annotation(self):
        image, annotation = self.sample()
        image.write_bytes(b"")
        annotation.write_bytes(b"\xff")
        codes = self.codes(self.report())
        self.assertIn("empty_image", codes)
        self.assertIn("annotation_read_error", codes)

    def test_empty_labels_and_boundary_attributes_require_review(self):
        self.sample("\n")
        self.assertEqual(self.report()["status"], "warning")
        self.assertIn("empty_annotation", self.codes(self.report()))
        _, annotation = self.sample("-1,0,1,1,1,1,-1,-1\n")
        original = annotation.read_bytes()
        report = self.report()
        self.assertEqual(self.codes(report), {"negative_bbox_origin", "unusual_attributes"})
        self.assertEqual(annotation.read_bytes(), original)

    def test_duplicate_check_is_opt_in_and_detects_cross_split_copy(self):
        self.sample()
        self.sample(split="val")
        report = validate_dataset(self.root, ("train", "val"))
        self.assertEqual(report["duplicate_check"], "not_run")
        self.assertEqual(report["status"], "passed")
        report = validate_dataset(self.root, ("train", "val"), check_duplicates=True)
        self.assertEqual(report["status"], "failed")
        self.assertIn("cross_split_duplicate", self.codes(report))

    def test_within_split_duplicate_warns(self):
        self.sample()
        self.sample(name="copy")
        report = self.report(check_duplicates=True)
        self.assertEqual(report["status"], "warning")
        self.assertIn("within_split_duplicate", self.codes(report))

    def test_unknown_repeated_splits_and_missing_root_rejected(self):
        for splits in ((), ("train", "train"), ("test-challenge",), ("../other",)):
            with self.subTest(splits=splits), self.assertRaises(ValueError):
                validate_dataset(self.root, splits)
        with self.assertRaises(ValueError):
            validate_dataset(self.root / "absent")

    def test_cli_json_and_report_preserve_existing_file(self):
        self.sample()
        output = Path(self.temporary.name) / "outputs" / "validation.json"
        result = self.cli("--report", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(output.read_text()))
        original = output.read_bytes()
        result = self.cli("--report", output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_bytes(), original)

    def test_cli_error_warning_and_usage_exit_codes(self):
        self.sample("0,0,-1,1,1,1,0,0\n")
        self.assertEqual(self.cli().returncode, 1)
        self.sample("\n")
        self.assertEqual(self.cli().returncode, 0)
        self.assertEqual(self.cli("--splits", "train", "train").returncode, 2)
        self.assertEqual(self.cli("--splits", "test-challenge").returncode, 2)
        self.assertEqual(self.cli("--root", self.root / "absent").returncode, 2)

    def test_report_inside_dataset_rejected(self):
        self.sample()
        report = self.root / "report.json"
        self.assertEqual(self.cli("--report", report).returncode, 2)
        self.assertFalse(report.exists())

    def test_nonempty_image_is_not_claimed_to_be_decoded(self):
        image, _ = self.sample()
        image.write_bytes(b"not a decoded image")
        report = self.report()
        self.assertEqual(report["status"], "passed")
        self.assertIn("full_image_decoding", report["not_checked"])
        self.assertIn("bbox_vs_image_dimensions", report["not_checked"])


if __name__ == "__main__":
    unittest.main()
