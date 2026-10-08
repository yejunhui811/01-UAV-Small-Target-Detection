"""End-to-end synthetic checks for preparation audits, including tampering."""

from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from extract_visdrone import extract_archives
from audit_visdrone_preparation import audit
from uav_small_target.visdrone_yolo import convert_dataset


class PreparationAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="uav-preparation-audit-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        archives = base / "archives"
        archives.mkdir()
        image_bytes = BytesIO()
        with Image.new("RGB", (100, 80)) as image:
            image.save(image_bytes, format="PNG")
        for split in ("train", "val"):
            with zipfile.ZipFile(archives / f"VisDrone2019-DET-{split}.zip", "w") as archive:
                archive.writestr(f"VisDrone2019-DET-{split}/images/sample.png", image_bytes.getvalue())
                archive.writestr(f"VisDrone2019-DET-{split}/annotations/sample.txt",
                                 "10,20,20,10,1,4,0,0\n1,2,3,0,1,4,0,0\n0,0,1,1,0,0,0,0\n")
        self.raw, self.metadata, self.derived = (base / name for name in ("raw", "metadata", "derived"))
        extract_archives(archives, self.raw, self.metadata)
        convert_dataset(self.raw, self.derived, zero_area_policy="exclude", synthetic=True)

    def run_audit(self):
        return audit(self.raw, self.derived, self.metadata / "file-manifest.jsonl")

    def test_complete_audit_counts_and_geometry(self):
        report = self.run_audit()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["raw_files_verified"], 4)
        self.assertEqual(report["splits"]["train"]["target_rows"], 1)
        self.assertEqual(report["splits"]["val"]["excluded_zero_area_rows"], 1)

    def test_changed_raw_or_copied_image_is_detected(self):
        raw_image = self.raw / "VisDrone2019-DET-train/images/sample.png"
        before = raw_image.read_bytes()
        raw_image.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Raw file changed"):
            self.run_audit()
        raw_image.write_bytes(before)
        (self.derived / "images/train/sample.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Image copy changed"):
            self.run_audit()

    def test_changed_label_or_extra_raw_file_is_detected(self):
        label = self.derived / "labels/train/sample.txt"
        before = label.read_bytes()
        label.write_text("3 0.5 0.5 0.1 0.1\n")
        with self.assertRaisesRegex(ValueError, "Label hash mismatch"):
            self.run_audit()
        label.write_bytes(before)
        (self.raw / "unexpected.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            self.run_audit()


if __name__ == "__main__":
    unittest.main()
