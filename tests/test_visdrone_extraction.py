"""Synthetic ZIP tests; no dataset download."""

import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from extract_visdrone import extract_archives


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="uav-extract-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.archives, self.raw, self.metadata = (self.base / n for n in ("archives", "raw", "metadata"))
        self.archives.mkdir()
        for split in ("train", "val"):
            self.make_zip(split)

    def make_zip(self, split, extra=None):
        path = self.archives / f"VisDrone2019-DET-{split}.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f"{path.stem}/images/sample.jpg", b"synthetic bytes, not an image")
            archive.writestr(f"{path.stem}/annotations/sample.txt", b"1,2,3,4,1,1,0,0\n")
            if extra is not None:
                archive.writestr(extra, b"extra")
        return path

    def extract(self):
        return extract_archives(self.archives, self.raw, self.metadata)

    def test_hashes_crc_manifest_and_archive_preservation(self):
        before = {p: p.read_bytes() for p in self.archives.iterdir()}
        report = self.extract()
        self.assertEqual([a["files"] for a in report["archives"]], [2, 2])
        rows = [json.loads(line) for line in (self.metadata / "file-manifest.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 4)
        for row in rows:
            content = (self.raw / row["path"]).read_bytes()
            self.assertEqual(row["size_bytes"], len(content))
            self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_traversal_absolute_backslash_unexpected_and_duplicate_paths_rejected(self):
        for name in ("../escape", "/absolute", "VisDrone2019-DET-train/../escape",
                     "VisDrone2019-DET-train\\escape", "unexpected/file",
                     "VisDrone2019-DET-train/images/SAMPLE.jpg"):
            with self.subTest(name=name):
                self.make_zip("train", name)
                with self.assertRaises(ValueError):
                    self.extract()
                self.assertFalse(self.raw.exists())
                self.assertFalse(self.metadata.exists())
                self.assertFalse(list(self.base.glob(".uav-extract-*")))

    def test_symlink_entry_rejected(self):
        info = zipfile.ZipInfo("VisDrone2019-DET-train/link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.make_zip("train", info)
        with self.assertRaises(ValueError):
            self.extract()

    def test_existing_outputs_and_nested_paths_preserved(self):
        self.raw.mkdir()
        marker = self.raw / "user.txt"
        marker.write_text("preserve")
        with self.assertRaises(ValueError):
            self.extract()
        self.assertEqual(marker.read_text(), "preserve")
        with self.assertRaises(ValueError):
            extract_archives(self.archives, self.archives / "raw", self.metadata)

    def test_corrupt_archive_after_train_is_staged_does_not_publish(self):
        path = self.make_zip("val")
        path.write_bytes(b"not a ZIP")
        with self.assertRaises(zipfile.BadZipFile):
            self.extract()
        self.assertFalse(self.raw.exists())
        self.assertFalse(self.metadata.exists())


if __name__ == "__main__":
    unittest.main()
