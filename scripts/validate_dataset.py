#!/usr/bin/env python3
"""Validate structural and counterfactual-pair invariants for the pilot set."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "pilot_v1.jsonl"


def main() -> int:
    errors: list[str] = []
    records = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(records) != 192:
        errors.append(f"expected 192 samples, found {len(records)}")

    ids = [record["sample_id"] for record in records]
    if len(ids) != len(set(ids)):
        errors.append("sample_id values are not unique")

    pairs: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        pairs[record["pair_id"]].append(record)
        expected_turns = record["variables"]["turn_count"]
        if len(record["turns"]) != expected_turns:
            errors.append(f"{record['sample_id']}: expected {expected_turns} turns")
        estimated = record["context_stats"]["estimated_tokens"]
        target = record["variables"]["target_context_tokens"]
        if abs(estimated - target) / target > 0.05:
            errors.append(f"{record['sample_id']}: token estimate {estimated} is not within 5% of {target}")
        for turn in record["turns"]:
            for image in turn["user"]["images"]:
                if not (ROOT / image).exists():
                    errors.append(f"{record['sample_id']}: missing image {image}")

    if len(pairs) != 96:
        errors.append(f"expected 96 counterfactual pairs, found {len(pairs)}")
    for pair_id, pair in pairs.items():
        if {item["label"] for item in pair} != {"safe", "unsafe"}:
            errors.append(f"{pair_id}: pair must contain one safe and one unsafe sample")
            continue
        safe = next(item for item in pair if item["label"] == "safe")
        unsafe = next(item for item in pair if item["label"] == "unsafe")
        if safe["turns"][:-1] != unsafe["turns"][:-1]:
            errors.append(f"{pair_id}: pre-final turns differ across the pair")

    category_counts = Counter(record["risk_category"] for record in records)
    if set(category_counts.values()) != {48}:
        errors.append(f"risk categories are not balanced: {dict(category_counts)}")
    condition_counts = Counter(record["condition_id"] for record in records)
    if set(condition_counts.values()) != {24}:
        errors.append(f"conditions are not balanced: {dict(condition_counts)}")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation passed: {len(records)} samples, {len(pairs)} pairs")
    print(f"Category counts: {dict(sorted(category_counts.items()))}")
    print(f"Condition counts: {dict(sorted(condition_counts.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

