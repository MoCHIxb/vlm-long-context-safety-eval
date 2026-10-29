#!/usr/bin/env python3
"""Validate formal_v3 seed-bank structure and report approval readiness."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "seeds" / "formal_v3_calibration_candidates.json"
TAXONOMY = ROOT / "configs" / "formal_v3_taxonomy.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(record: dict[str, Any], keys: set[str], context: str) -> None:
    missing = sorted(keys - record.keys())
    if missing:
        raise ValueError(f"{context} missing keys: {missing}")


def validate_record(record: dict[str, Any], taxonomy: dict[str, Any]) -> list[str]:
    require(
        record,
        {"seed_id", "status", "split", "scene_type", "source", "evidence_packets", "review"},
        record.get("seed_id", "<unknown>"),
    )
    seed_id = record["seed_id"]
    packets = record["evidence_packets"]
    minimum_packets = 3 if record["scene_type"] == "harmful" else 2
    if not minimum_packets <= len(packets) <= 4:
        raise ValueError(
            f"{seed_id} must contain {minimum_packets}-4 evidence packets, got {len(packets)}"
        )
    images = [image for packet in packets for image in packet.get("images", [])]
    if len(images) != len(set(images)):
        raise ValueError(f"{seed_id} repeats an image within its evidence set")
    if record["scene_type"] == "harmful":
        require(record, {"risk_category", "risk_subcategory", "dialogue_atoms", "expected_behavior"}, seed_id)
        allowed = taxonomy["harmful"].get(record["risk_category"], [])
        if record["risk_subcategory"] not in allowed:
            raise ValueError(f"{seed_id} has invalid harmful subcategory")
    elif record["scene_type"] == "benign":
        require(record, {"benign_subcategory", "dialogue_outline", "final_request"}, seed_id)
        if record["benign_subcategory"] not in taxonomy["benign"]:
            raise ValueError(f"{seed_id} has invalid benign subcategory")
    else:
        raise ValueError(f"{seed_id} has invalid scene_type: {record['scene_type']}")

    unresolved: list[str] = []
    serialized = json.dumps(record, ensure_ascii=False)
    if "TO_" in serialized:
        unresolved.append("contains_unresolved_authoring_fields")
    if not all(value for key, value in record["review"].items() if key != "reviewer_ids"):
        unresolved.append("review_incomplete")
    if len(record["review"].get("reviewer_ids", [])) < 2:
        unresolved.append("fewer_than_two_reviewers")
    return unresolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    bank = load(args.input)
    taxonomy = load(TAXONOMY)
    records = list(bank.get("harmful", [])) + list(bank.get("benign", []))
    ids = [record["seed_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate seed_id values detected")

    unresolved: dict[str, list[str]] = {}
    for record in records:
        reasons = validate_record(record, taxonomy)
        if reasons:
            unresolved[record["seed_id"]] = reasons

    summary = {
        "input": str(args.input),
        "structurally_valid": True,
        "harmful_count": len(bank.get("harmful", [])),
        "benign_count": len(bank.get("benign", [])),
        "risk_category_counts": dict(Counter(r["risk_category"] for r in bank.get("harmful", []))),
        "approved_count": len(records) - len(unresolved),
        "not_approved_count": len(unresolved),
        "not_approved": unresolved,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
