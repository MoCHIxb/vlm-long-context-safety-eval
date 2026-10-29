#!/usr/bin/env python3
"""Validate formal_v3 scale, pairing, schedules, lengths, images, and seed quotas."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "formal_v3.json"
TAXONOMY_PATH = ROOT / "configs" / "formal_v3_taxonomy.json"
SEED_BANK_PATH = ROOT / "data" / "seeds" / "formal_v3_seed_bank.json"
DATASET_PATH = ROOT / "data" / "processed" / "formal_v3.jsonl"
SUMMARY_PATH = ROOT / "documentation" / "reports" / "formal_v3_validation.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_images(record: dict[str, Any]) -> list[str]:
    return [image for turn in record["turns"] for image in turn["user"]["images"]]


def text_history(record: dict[str, Any]) -> list[tuple[str, str | None]]:
    return [(turn["user"]["content"], turn.get("assistant_context")) for turn in record["turns"]]


def validate_seed_bank(bank: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any]:
    harmful = bank["harmful"]
    benign = bank["benign"]
    assert len(harmful) == 80
    assert len(benign) == 64
    assert len({item["seed_id"] for item in harmful + benign}) == 144
    assert Counter(item["risk_category"] for item in harmful) == Counter({name: 20 for name in taxonomy["harmful"]})
    assert all(count == 5 for count in Counter(item["risk_subcategory"] for item in harmful).values())
    assert all(count == 8 for count in Counter(item["benign_subcategory"] for item in benign).values())
    harmful_splits = Counter((item["risk_category"], item["split"]) for item in harmful)
    for category in taxonomy["harmful"]:
        assert harmful_splits[(category, "calibration")] == 2
        assert harmful_splits[(category, "primary")] == 14
        assert harmful_splits[(category, "heldout")] == 4
    assert Counter(item["split"] for item in benign) == Counter({"calibration": 8, "primary": 40, "heldout": 16})
    assert all(len(item["evidence_packets"]) in {3, 4} for item in harmful)
    assert all(len(item["evidence_packets"]) in {2, 3, 4} for item in benign)
    assert len({item["source"]["source_ids"][0] for item in harmful}) == 80
    assert len({item["source"]["source_ids"][0] for item in benign}) == 64

    def tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    near_duplicates = []
    max_similarity = 0.0
    for collection in (harmful, benign):
        for left_index, left in enumerate(collection):
            left_tokens = tokens(left["topic"])
            for right in collection[left_index + 1:]:
                right_tokens = tokens(right["topic"])
                union = left_tokens | right_tokens
                similarity = len(left_tokens & right_tokens) / len(union) if union else 1.0
                max_similarity = max(max_similarity, similarity)
                if similarity >= 0.90:
                    near_duplicates.append((left["seed_id"], right["seed_id"], round(similarity, 4)))
    assert not near_duplicates, f"Near-duplicate seed topics: {near_duplicates[:5]}"

    image_to_seeds: dict[str, set[str]] = defaultdict(set)
    for seed in harmful + benign:
        images = [image for packet in seed["evidence_packets"] for image in packet["images"]]
        assert len(images) == len(set(images))
        for image in images:
            assert (ROOT / image).is_file(), f"Missing image: {image}"
            image_to_seeds[image].add(seed["seed_id"])
    cross_seed_images = {image: sorted(ids) for image, ids in image_to_seeds.items() if len(ids) > 1}
    assert not cross_seed_images, f"Images shared across seeds: {list(cross_seed_images.items())[:5]}"
    return {
        "harmful_seed_count": len(harmful), "benign_seed_count": len(benign),
        "cross_seed_image_reuse": len(cross_seed_images),
        "topic_near_duplicate_threshold": 0.90,
        "topic_near_duplicate_pairs": len(near_duplicates),
        "maximum_topic_jaccard_similarity": round(max_similarity, 6),
        "harmful_split_counts": dict(Counter(item["split"] for item in harmful)),
        "benign_split_counts": dict(Counter(item["split"] for item in benign)),
    }


def validate_records(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    expected = config["expected_sizes"]
    assert len(records) == expected["total_trajectories"]
    assert len({item["sample_id"] for item in records}) == len(records)
    assert Counter(item["track"] for item in records) == Counter({"harmful_controlled": 3840, "benign_controlled": 384})
    assert Counter(item["variables"]["visual_evidence_schedule"] for item in records) == Counter({"static_initial_bundle": 2112, "dynamic_incremental": 2112})
    assert len({item["seed_id"] for item in records if item["track"] == "harmful_controlled"}) == 80
    assert len({item["seed_id"] for item in records if item["track"] == "benign_controlled"}) == 64

    harmful_conditions = Counter(item["condition_id"] for item in records if item["track"] == "harmful_controlled")
    benign_conditions = Counter(item["condition_id"] for item in records if item["track"] == "benign_controlled")
    assert all(value == 320 for value in harmful_conditions.values()) and len(harmful_conditions) == 12
    assert all(value == 128 for value in benign_conditions.values()) and len(benign_conditions) == 3
    assert Counter(item["label"] for item in records if item["track"] == "harmful_controlled") == Counter({"safe": 1920, "unsafe": 1920})

    safe_unsafe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    schedules: dict[str, list[dict[str, Any]]] = defaultdict(list)
    deviations = []
    image_references = 0
    for record in records:
        target = record["variables"]["target_context_tokens"]
        actual = record["context_stats"]["estimated_tokens"]
        deviations.append(abs(actual - target) / target)
        assert abs(actual - target) / target <= 0.02, (record["sample_id"], actual, target)
        images = aggregate_images(record)
        image_references += len(images)
        assert len(images) == len(set(images)), f"Repeated image in {record['sample_id']}"
        assert all((ROOT / image).is_file() for image in images)
        if record["pair_id"]:
            safe_unsafe[record["pair_id"]].append(record)
        schedules[record["schedule_pair_id"]].append(record)

    assert len(safe_unsafe) == 1920
    for pair_id, pair in safe_unsafe.items():
        assert len(pair) == 2 and {item["label"] for item in pair} == {"safe", "unsafe"}, pair_id
        safe = next(item for item in pair if item["label"] == "safe")
        unsafe = next(item for item in pair if item["label"] == "unsafe")
        assert len(safe["turns"]) == len(unsafe["turns"])
        assert text_history(safe)[:-1] == text_history(unsafe)[:-1]
        assert aggregate_images(safe) == aggregate_images(unsafe)
        assert safe["turns"][-1]["user"]["content"] != unsafe["turns"][-1]["user"]["content"]

    assert len(schedules) == 2112
    for pair_id, pair in schedules.items():
        assert len(pair) == 2, pair_id
        assert {item["variables"]["visual_evidence_schedule"] for item in pair} == {"static_initial_bundle", "dynamic_incremental"}
        static = next(item for item in pair if item["variables"]["visual_evidence_schedule"] == "static_initial_bundle")
        dynamic = next(item for item in pair if item["variables"]["visual_evidence_schedule"] == "dynamic_incremental")
        assert text_history(static) == text_history(dynamic)
        assert sorted(aggregate_images(static)) == sorted(aggregate_images(dynamic))
        assert static["turns"][0]["user"]["images"] == aggregate_images(static)
        assert any(turn["user"]["images"] for turn in dynamic["turns"][1:])

    return {
        "trajectory_count": len(records), "track_counts": dict(Counter(item["track"] for item in records)),
        "schedule_counts": dict(Counter(item["variables"]["visual_evidence_schedule"] for item in records)),
        "safe_unsafe_pair_count": len(safe_unsafe), "schedule_pair_count": len(schedules),
        "image_reference_count": image_references, "max_relative_token_deviation": max(deviations),
    }


def main() -> None:
    config = load(CONFIG_PATH)
    taxonomy = load(TAXONOMY_PATH)
    bank = load(SEED_BANK_PATH)
    records = load_jsonl(DATASET_PATH)
    summary = {
        "status": "structurally_valid_machine_constructed_unreviewed",
        "seed_bank": validate_seed_bank(bank, taxonomy),
        "dataset": validate_records(records, config),
        "files": {
            "seed_bank_sha256": sha256(SEED_BANK_PATH),
            "dataset_sha256": sha256(DATASET_PATH),
            "dataset_bytes": DATASET_PATH.stat().st_size,
        },
        "human_review": {
            "required": True, "completed": False,
            "note": "No human reviewer identities or approvals are fabricated by the build pipeline."
        }
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
