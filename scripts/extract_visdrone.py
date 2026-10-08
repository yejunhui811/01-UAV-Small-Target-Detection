"""Safely extract local DET train/val ZIPs and record archive/file hashes."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


def extract_archives(archive_dir, raw_root, metadata_dir):
    """Validate paths, stream CRC-checked extraction, publish new directories only.

    A file manifest includes every extracted file. SHA-256 is a local fingerprint,
    not an official authenticity check. No network or image/model code runs.
    """
    destinations = [Path(raw_root), Path(metadata_dir)]
    if any(p.exists() or p.is_symlink() for p in destinations):
        raise ValueError("Raw/metadata output already exists; choose new directories")
    archive_dir, raw_root, metadata_dir = map(lambda p: Path(p).resolve(),
                                             (archive_dir, raw_root, metadata_dir))
    if any(a.is_relative_to(b) or b.is_relative_to(a)
           for a, b in ((raw_root, metadata_dir), (raw_root, archive_dir), (metadata_dir, archive_dir))):
        raise ValueError("Archive, raw and metadata directories must be separate, non-nested")
    archives = [archive_dir / f"VisDrone2019-DET-{split}.zip" for split in ("train", "val")]
    report = {"schema_version": 1, "scope": "zip_crc_paths_and_local_sha256",
              "archives": [], "official_hash_comparison": "not_available",
              "not_checked": ["release_authenticity", "annotation_semantics", "image_decoding"]}
    raw_root.parent.mkdir(parents=True, exist_ok=True)
    metadata_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".uav-extract-", dir=raw_root.parent) as temporary:
        stage = Path(temporary)
        raw_stage, meta_stage = stage / "raw", stage / "metadata"
        raw_stage.mkdir()
        meta_stage.mkdir()
        with (meta_stage / "file-manifest.jsonl").open("w", encoding="utf-8") as manifest:
            for archive_path in archives:
                with archive_path.open("rb") as handle:
                    archive_hash = hashlib.file_digest(handle, "sha256").hexdigest()
                with zipfile.ZipFile(archive_path) as archive:
                    entries = archive.infolist()
                    if len(entries) > 30000 or sum(e.file_size for e in entries) > 20 * 1024**3:
                        raise ValueError("Archive exceeds DET extraction limits")
                    seen = set()
                    for entry in entries:
                        name, parts = entry.filename, PurePosixPath(entry.filename).parts
                        mode = entry.external_attr >> 16
                        if (not parts or name.startswith("/") or "\\" in name or ":" in name
                                or any(p in (".", "..") for p in name.rstrip("/").split("/"))
                                or any(ord(c) < 32 for c in name)
                                or parts[0] != archive_path.stem
                                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))):
                            raise ValueError(f"Unsafe/unexpected ZIP entry: {name!r}")
                        folded = name.rstrip("/").casefold()
                        if folded in seen:
                            raise ValueError(f"Duplicate/case-colliding ZIP path: {name!r}")
                        seen.add(folded)
                    count, total_bytes = 0, 0
                    for entry in entries:
                        destination = raw_stage / entry.filename
                        if entry.is_dir():
                            destination.mkdir(parents=True, exist_ok=True)
                            continue
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        digest = hashlib.sha256()
                        size = 0
                        with archive.open(entry) as source, destination.open("xb") as output:
                            while chunk := source.read(1024 * 1024):
                                output.write(chunk)
                                digest.update(chunk)
                                size += len(chunk)
                        if size != entry.file_size:
                            raise ValueError(f"Size mismatch for {entry.filename}")
                        manifest.write(json.dumps({"archive": archive_path.name,
                            "path": destination.relative_to(raw_stage).as_posix(),
                            "size_bytes": size, "sha256": digest.hexdigest()}) + "\n")
                        count += 1
                        total_bytes += size
                    report["archives"].append({"name": archive_path.name,
                        "size_bytes": archive_path.stat().st_size, "sha256": archive_hash,
                        "crc": "passed_all_extracted_files", "files": count,
                        "uncompressed_bytes": total_bytes})
        with (meta_stage / "file-manifest.jsonl").open("rb") as handle:
            report["file_manifest_sha256"] = hashlib.file_digest(handle, "sha256").hexdigest()
        (meta_stage / "extraction.json").write_text(json.dumps(report, indent=2) + "\n")
        # Publication is not atomic across directories; I/O failure can leave a
        # newly reserved incomplete output. Existing outputs are never removed.
        for destination, source in ((raw_root, raw_stage), (metadata_dir, meta_stage)):
            destination.mkdir()
            for artifact in source.iterdir():
                shutil.move(str(artifact), str(destination / artifact.name))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = extract_archives(args.archive_dir, args.raw_root, args.metadata_dir)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"Extraction failed: {exc}\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
