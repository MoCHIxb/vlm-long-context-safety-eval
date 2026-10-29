#!/usr/bin/env python3
"""Write canonical formal_v3 JSONL shards and a checksum manifest."""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "formal_v3.jsonl"
OUTPUT = ROOT / "data" / "processed" / "formal_v3_shards"

SHARD_NAMES = {
    "deception_and_economic_harm": "harmful_deception_and_economic_harm.jsonl",
    "privacy_and_profiling": "harmful_privacy_and_profiling.jsonl",
    "illegal_and_cyber_abuse": "harmful_illegal_and_cyber_abuse.jsonl",
    "physical_and_public_safety": "harmful_physical_and_public_safety.jsonl",
    "none": "benign_controlled.jsonl",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    handles = {category: (OUTPUT / name).open("w", encoding="utf-8", newline="\n") for category, name in SHARD_NAMES.items()}
    counts: Counter[str] = Counter()
    try:
        with INPUT.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                record: dict[str, Any] = json.loads(line)
                category = record["risk_category"]
                handles[category].write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[category] += 1
    finally:
        for handle in handles.values():
            handle.close()

    files = []
    for category, filename in SHARD_NAMES.items():
        path = OUTPUT / filename
        compressed = path.with_suffix(path.suffix + ".gz")
        with path.open("rb") as source, compressed.open("wb") as raw_destination:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_destination, compresslevel=9, mtime=0
            ) as destination:
                shutil.copyfileobj(source, destination)
        files.append({
            "path": path.relative_to(ROOT).as_posix(), "category": category,
            "record_count": counts[category], "bytes": path.stat().st_size, "sha256": sha256(path),
            "compressed_path": compressed.relative_to(ROOT).as_posix(),
            "compressed_bytes": compressed.stat().st_size,
            "compressed_sha256": sha256(compressed),
        })
    manifest = {
        "dataset": "LongContextMultiTurnVLMSafety-Formal-v3",
        "schema_version": "4.0.0-draft",
        "status": "structurally_valid_machine_constructed_unreviewed",
        "total_records": sum(counts.values()), "files": files,
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
