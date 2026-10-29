#!/usr/bin/env python3
"""Prepare independent human-review files for the formal_v3 seed bank."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "seeds" / "formal_v3_seed_bank.json"
OUTPUT_DIR = ROOT / "data" / "review"


def review_item(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed_id": seed["seed_id"], "scene_type": seed["scene_type"], "split": seed["split"],
        "risk_category": seed.get("risk_category"), "risk_subcategory": seed.get("risk_subcategory"),
        "benign_subcategory": seed.get("benign_subcategory"), "topic": seed["topic"],
        "evidence_packets": seed["evidence_packets"],
        "dialogue_atoms": seed.get("dialogue_atoms"),
        "dialogue_outline": seed.get("dialogue_outline"), "final_request": seed.get("final_request"),
        "source": seed["source"],
        "review": {
            "source_and_license_valid": None,
            "images_factually_coherent": None,
            "category_assignment_correct": None,
            "independent_scene": None,
            "safe_unsafe_semantically_matched": None if seed["scene_type"] == "benign" else None,
            "static_dynamic_pair_constructible": None,
            "c09_redundant_natural": None if seed["scene_type"] == "benign" else None,
            "c10_conflicting_natural": None if seed["scene_type"] == "benign" else None,
            "c11_clarification_natural": None if seed["scene_type"] == "benign" else None,
            "decision": None,
            "revision_notes": ""
        }
    }


def main() -> None:
    bank = json.loads(INPUT.read_text(encoding="utf-8"))
    items = [review_item(seed) for seed in bank["harmful"] + bank["benign"]]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for reviewer, seed_value in (("reviewer_a", 3107), ("reviewer_b", 7919)):
        ordered = list(items)
        random.Random(seed_value).shuffle(ordered)
        path = OUTPUT_DIR / f"formal_v3_seed_review_{reviewer}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for item in ordered:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Wrote {len(ordered)} items to {path}")


if __name__ == "__main__":
    main()
