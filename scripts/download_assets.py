#!/usr/bin/env python3
"""Download the selected SafeMT images and write a checksum manifest."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEEDS_PATH = ROOT / "data" / "seeds" / "pilot_seeds.json"
MANIFEST_PATH = ROOT / "data" / "raw" / "source_manifest.json"
BASE_URL = "https://huggingface.co/datasets/HappyCorpse/SafeMT/resolve/main/data/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    seeds = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    files = []
    for seed in seeds:
        target = ROOT / seed["local_image"]
        target.parent.mkdir(parents=True, exist_ok=True)
        url = BASE_URL + seed["source_image_path"]
        if not target.exists():
            print(f"Downloading {seed['seed_id']} from {url}")
            urllib.request.urlretrieve(url, target)
        files.append(
            {
                "seed_id": seed["seed_id"],
                "source_dataset": "HappyCorpse/SafeMT",
                "license": "CC BY-NC 4.0",
                "url": url,
                "local_path": seed["local_image"],
                "bytes": target.stat().st_size,
                "sha256": sha256(target),
            }
        )
    MANIFEST_PATH.write_text(json.dumps({"files": files}, indent=2), encoding="utf-8", newline="\n")
    print(f"Verified {len(files)} images and wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()

