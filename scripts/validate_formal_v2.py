#!/usr/bin/env python3
"""Validate formal_v2 scale, source diversity, length controls, and assets."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "formal_v2.jsonl"
EXPECTED_TRACKS = {
    "static_visual_anchor": 264,
    "dynamic_risk_trajectory": 160,
    "benign_multi_image_control": 32,
    "mmds_breadth_length": 768,
    "mmdu_benign_length": 330,
}


def main() -> int:
    records = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line]
    errors: list[str] = []
    tracks = Counter(record["track"] for record in records)
    if len(records) != 1554:
        errors.append(f"expected 1554 samples, found {len(records)}")
    if tracks != EXPECTED_TRACKS:
        errors.append(f"unexpected track counts: {dict(tracks)}")
    ids = [record["sample_id"] for record in records]
    if len(ids) != len(set(ids)):
        errors.append("sample_id values are not unique")

    mmds = [record for record in records if record["track"] == "mmds_breadth_length"]
    mmdu = [record for record in records if record["track"] == "mmdu_benign_length"]
    if len({record["seed_id"] for record in mmds}) != 192:
        errors.append("MMDS breadth must contain 192 independent semantic seeds")
    if len({record["seed_id"] for record in mmdu}) != 110:
        errors.append("MMDU breadth must contain 110 independent semantic seeds")
    category_seeds: dict[str, set[str]] = defaultdict(set)
    for record in mmds:
        category_seeds[record["risk_category"]].add(record["seed_id"])
    if {key: len(value) for key, value in category_seeds.items()} != {
        "deception_and_economic_harm": 48,
        "privacy_and_profiling": 48,
        "illegal_and_cyber_abuse": 48,
        "physical_and_public_safety": 48,
    }:
        errors.append(f"MMDS semantic seeds are not balanced: {dict((k, len(v)) for k, v in category_seeds.items())}")

    breadth_conditions = Counter(record["condition_id"] for record in mmds)
    if breadth_conditions != {"MB00": 192, "MB01": 192, "MB02": 192, "MB03": 192}:
        errors.append(f"unexpected MMDS condition counts: {dict(breadth_conditions)}")
    benign_conditions = Counter(record["condition_id"] for record in mmdu)
    if benign_conditions != {"LB01": 110, "LB02": 110, "LB03": 110}:
        errors.append(f"unexpected MMDU condition counts: {dict(benign_conditions)}")

    for record in records:
        if len(record["turns"]) != record["variables"]["turn_count"]:
            errors.append(f"{record['sample_id']}: turn count mismatch")
        if record["evaluation_target"]["primary_turn"] != len(record["turns"]):
            errors.append(f"{record['sample_id']}: final turn is not the evaluation target")
        target = record["variables"].get("target_context_tokens")
        if target and abs(record["context_stats"]["estimated_tokens"] - target) / target > 0.05:
            errors.append(f"{record['sample_id']}: context length exceeds 5% tolerance")
        for turn in record["turns"]:
            for image in turn["user"]["images"]:
                if not (ROOT / image).is_file():
                    errors.append(f"{record['sample_id']}: missing image {image}")

    if errors:
        print("Validation failed:")
        for error in errors[:100]:
            print(f"- {error}")
        return 1
    print(f"Validation passed: {len(records)} samples across {len(tracks)} tracks")
    print(f"Track counts: {dict(sorted(tracks.items()))}")
    print("Independent breadth seeds: MMDS=192, MMDU=110")
    return 0


if __name__ == "__main__":
    sys.exit(main())
