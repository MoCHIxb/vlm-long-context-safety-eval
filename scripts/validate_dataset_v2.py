#!/usr/bin/env python3
"""Validate pilot_v2 track, pairing, trajectory, and asset invariants."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "pilot_v2.jsonl"


def main() -> int:
    errors: list[str] = []
    records = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_tracks = {"static_visual_anchor": 64, "dynamic_risk_trajectory": 64, "benign_multi_image_control": 32}
    track_counts = Counter(record["track"] for record in records)
    if len(records) != 160:
        errors.append(f"expected 160 samples, found {len(records)}")
    if track_counts != expected_tracks:
        errors.append(f"unexpected track counts: {dict(track_counts)}")

    ids = [record["sample_id"] for record in records]
    if len(ids) != len(set(ids)):
        errors.append("sample_id values are not unique")

    pairs: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if record["pair_id"]:
            pairs[record["pair_id"]].append(record)
        if len(record["turns"]) != record["variables"]["turn_count"]:
            errors.append(f"{record['sample_id']}: turn count mismatch")
        for turn in record["turns"]:
            for image in turn["user"]["images"]:
                if not (ROOT / image).is_file():
                    errors.append(f"{record['sample_id']}: missing image {image}")

        target = record["variables"]["target_context_tokens"]
        if target:
            estimated = record["context_stats"]["estimated_tokens"]
            if abs(estimated - target) / target > 0.05:
                errors.append(f"{record['sample_id']}: token estimate {estimated} differs from target {target}")

        images = {image for turn in record["turns"] for image in turn["user"]["images"]}
        if record["track"] == "static_visual_anchor" and len(images) != 1:
            errors.append(f"{record['sample_id']}: static track must contain exactly one image")
        if record["track"] in {"dynamic_risk_trajectory", "benign_multi_image_control"} and len(images) < 2:
            errors.append(f"{record['sample_id']}: multi-image track contains fewer than two images")
        if record["track"] == "benign_multi_image_control" and record["label"] != "safe":
            errors.append(f"{record['sample_id']}: benign control is not safe")

    if len(pairs) != 64:
        errors.append(f"expected 64 counterfactual pairs, found {len(pairs)}")
    for pair_id, pair in pairs.items():
        if {item["label"] for item in pair} != {"safe", "unsafe"}:
            errors.append(f"{pair_id}: pair must contain one safe and one unsafe sample")
            continue
        safe = next(item for item in pair if item["label"] == "safe")
        unsafe = next(item for item in pair if item["label"] == "unsafe")
        if safe["turns"][:-1] != unsafe["turns"][:-1]:
            errors.append(f"{pair_id}: pre-final histories differ")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation passed: {len(records)} samples, {len(pairs)} pairs")
    print(f"Track counts: {dict(sorted(track_counts.items()))}")
    print(f"Label counts: {dict(sorted(Counter(record['label'] for record in records).items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
