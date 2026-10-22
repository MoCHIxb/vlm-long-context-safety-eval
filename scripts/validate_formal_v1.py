#!/usr/bin/env python3
"""Validate formal_v1 balance, matched contrasts, trajectories, and assets."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "formal_v1.json"
DATASET_PATH = ROOT / "data" / "processed" / "formal_v1.jsonl"

EXPECTED_TRACKS = {
    "static_visual_anchor": 264,
    "dynamic_risk_trajectory": 160,
    "benign_multi_image_control": 32,
}
ALLOWED_CHANGES = {
    "turn_count": {"turn_count"},
    "context_length": {"context_bucket"},
    "risk_position": {"risk_position"},
    "risk_distribution": {"distribution"},
    "modality_relation": {"modality_relation"},
    "intent_clarification": {"clarification"},
    "image_timing": {"image_timing"},
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_config(config: dict, errors: list[str]) -> None:
    ignored = {"condition_id", "factor_under_test"}
    for track_name in ("static_track", "dynamic_track"):
        track = config[track_name]
        conditions = {item["condition_id"]: item for item in track["conditions"]}
        reference = conditions[track["reference_condition_id"]]
        for condition in conditions.values():
            factor = condition["factor_under_test"]
            if factor == "reference":
                continue
            changed = {
                key
                for key in set(reference) | set(condition)
                if key not in ignored and reference.get(key) != condition.get(key)
            }
            if changed != ALLOWED_CHANGES[factor]:
                errors.append(
                    f"{track_name}/{condition['condition_id']}: declared {factor} but changed {sorted(changed)}"
                )


def main() -> int:
    errors: list[str] = []
    config = load_json(CONFIG_PATH)
    validate_config(config, errors)
    records = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line]
    track_counts = Counter(record["track"] for record in records)
    if len(records) != 456:
        errors.append(f"expected 456 samples, found {len(records)}")
    if track_counts != EXPECTED_TRACKS:
        errors.append(f"unexpected track counts: {dict(track_counts)}")

    ids = [record["sample_id"] for record in records]
    if len(ids) != len(set(ids)):
        errors.append("sample_id values are not unique")

    pairs: dict[str, list[dict]] = defaultdict(list)
    condition_counts = Counter((record["track"], record["condition_id"]) for record in records)
    risk_counts = Counter(
        record["risk_category"] for record in records if record["track"] != "benign_multi_image_control"
    )
    for record in records:
        if record["pair_id"]:
            pairs[record["pair_id"]].append(record)
        if len(record["turns"]) != record["variables"]["turn_count"]:
            errors.append(f"{record['sample_id']}: turn count mismatch")
        if record["evaluation_target"]["primary_turn"] != len(record["turns"]):
            errors.append(f"{record['sample_id']}: primary turn must be final")
        for turn in record["turns"]:
            for image in turn["user"]["images"]:
                if not (ROOT / image).is_file():
                    errors.append(f"{record['sample_id']}: missing image {image}")

        target = record["variables"].get("target_context_tokens")
        if target:
            estimated = record["context_stats"]["estimated_tokens"]
            if abs(estimated - target) / target > 0.05:
                errors.append(f"{record['sample_id']}: token estimate {estimated} differs from target {target}")

        image_turns = [turn for turn in record["turns"] if turn["user"]["images"]]
        images = {image for turn in image_turns for image in turn["user"]["images"]}
        track = record["track"]
        if track == "static_visual_anchor":
            expected = 0 if record["variables"]["modality_relation"] == "text_only" else 1
            if len(images) != expected:
                errors.append(f"{record['sample_id']}: expected {expected} static images, found {len(images)}")
        elif track == "dynamic_risk_trajectory":
            if len(images) < 2:
                errors.append(f"{record['sample_id']}: dynamic trajectory has fewer than two images")
            if record["variables"]["image_timing"] == "final_bundle":
                if len(image_turns) != 1 or image_turns[0]["turn_index"] != len(record["turns"]):
                    errors.append(f"{record['sample_id']}: final bundle images are not confined to final turn")
            elif len(image_turns) < 2:
                errors.append(f"{record['sample_id']}: distributed condition needs multiple image turns")
        elif record["label"] != "safe" or len(images) < 2:
            errors.append(f"{record['sample_id']}: invalid benign multi-image control")

    if len(pairs) != 212:
        errors.append(f"expected 212 counterfactual pairs, found {len(pairs)}")
    for pair_id, pair in pairs.items():
        if len(pair) != 2 or {item["label"] for item in pair} != {"safe", "unsafe"}:
            errors.append(f"{pair_id}: pair must contain one safe and one unsafe sample")
            continue
        safe = next(item for item in pair if item["label"] == "safe")
        unsafe = next(item for item in pair if item["label"] == "unsafe")
        if safe["turns"][:-1] != unsafe["turns"][:-1]:
            errors.append(f"{pair_id}: pre-final histories differ")
        if safe["turns"][-1]["user"]["images"] != unsafe["turns"][-1]["user"]["images"]:
            errors.append(f"{pair_id}: final images differ")

    expected_risk_counts = {
        "deception_and_economic_harm": 106,
        "privacy_and_profiling": 106,
        "illegal_and_cyber_abuse": 106,
        "physical_and_public_safety": 106,
    }
    if risk_counts != expected_risk_counts:
        errors.append(f"risk categories are not balanced: {dict(risk_counts)}")
    for condition in config["static_track"]["conditions"]:
        if condition_counts[("static_visual_anchor", condition["condition_id"])] != 24:
            errors.append(f"{condition['condition_id']}: expected 24 static samples")
    for condition in config["dynamic_track"]["conditions"]:
        if condition_counts[("dynamic_risk_trajectory", condition["condition_id"])] != 16:
            errors.append(f"{condition['condition_id']}: expected 16 dynamic samples")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation passed: {len(records)} samples, {len(pairs)} pairs")
    print(f"Track counts: {dict(sorted(track_counts.items()))}")
    print(f"Label counts: {dict(sorted(Counter(record['label'] for record in records).items()))}")
    print(f"Risk counts: {dict(sorted(risk_counts.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
