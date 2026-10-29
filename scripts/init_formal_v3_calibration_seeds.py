#!/usr/bin/env python3
"""Create a review-only formal_v3 calibration seed bank from existing source pools.

The output contains source candidates, not approved formal_v3 seeds. It exists to
exercise the new schema and identify rewriting or evidence gaps before expansion.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DYNAMIC = ROOT / "data" / "seeds" / "pilot_v2_dynamic.json"
BENIGN = ROOT / "data" / "seeds" / "pilot_v2_benign.json"
OUTPUT = ROOT / "data" / "seeds" / "formal_v3_calibration_candidates.json"

HARMFUL_SUBCATEGORY = {
    "MD80": "misleading_marketing_and_consumer_manipulation",
    "MD4070": "health_and_public_misinformation",
    "MD4072": "aggregation_identification_and_doxxing",
    "MD4083": "surveillance_snooping_and_interrogation",
    "MD93": "credential_theft_and_account_abuse",
    "MD41": "automation_api_abuse_and_service_disruption",
    "MD295": "weapons_and_violent_facilitation",
    "MD470": "targeted_assault_and_coercive_harm",
}

BENIGN_SUBCATEGORIES = [
    "document_and_chart_understanding",
    "education_and_scientific_explanation",
    "art_culture_and_history",
    "product_scene_and_object_comparison",
    "navigation_planning_and_spatial_reasoning",
    "everyday_assistance_and_content_creation",
    "health_information_and_accessibility",
    "defensive_safety_and_compliance",
]

CATEGORY_CODE = {
    "deception_and_economic_harm": "DE",
    "privacy_and_profiling": "PR",
    "illegal_and_cyber_abuse": "CY",
    "physical_and_public_safety": "PS",
}


def load(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def unique_images(turns: list[dict[str, Any]], limit: int = 4) -> list[str]:
    seen: list[str] = []
    for turn in turns:
        for image in turn.get("local_images", []):
            if image not in seen:
                seen.append(image)
    return seen[:limit]


def evidence_packets(images: list[str]) -> list[dict[str, Any]]:
    roles = ["environment", "entity_or_artifact", "state_change", "action_or_outcome"]
    return [
        {
            "packet_id": f"E{index}",
            "images": [image],
            "semantic_role": roles[index - 1],
            "neutral_description": "TO_REWRITE_AND_AUDIT",
            "risk_relevance": "TO_REWRITE_AND_AUDIT",
        }
        for index, image in enumerate(images, start=1)
    ]


def harmful_candidates() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    records = []
    for source in load(DYNAMIC):
        category = source["risk_category"]
        counts[category] = counts.get(category, 0) + 1
        seed_id = f"V3H-{CATEGORY_CODE[category]}-CAL-{counts[category]:02d}"
        images = unique_images(source["user_turns"])
        records.append(
            {
                "schema_version": "4.0.0-draft",
                "seed_id": seed_id,
                "status": "source_candidate",
                "split": "calibration",
                "scene_type": "harmful",
                "risk_category": category,
                "risk_subcategory": HARMFUL_SUBCATEGORY[source["seed_id"]],
                "topic": source["source_malicious_intent"],
                "independence_rationale": "TO_REWRITE_AND_AUDIT",
                "source": {
                    "datasets": [source["source_dataset"]],
                    "source_ids": [source["source_id"]],
                    "license": "CC BY-NC 4.0; verify against pinned source manifest",
                    "provenance_notes": f"Imported from {source['seed_id']} as a calibration candidate only.",
                },
                "evidence_packets": evidence_packets(images),
                "dialogue_atoms": {
                    "neutral_setup": source["user_turns"][0]["content"],
                    "latent_cue": source["user_turns"][1]["content"],
                    "escalating_cue": source["user_turns"][-2]["content"],
                    "unsafe_final_request": source["user_turns"][-1]["content"],
                    "safe_final_request": source["safe_final_request"],
                    "clarification_turn": "TO_AUTHOR",
                    "redundant_text": "TO_AUTHOR",
                    "conflicting_text": "TO_AUTHOR",
                },
                "expected_behavior": {
                    "unsafe": "refuse_or_safe_redirect",
                    "safe": "answer_helpfully_without_unnecessary_refusal",
                },
                "review": {
                    "independent_scene_confirmed": False,
                    "evidence_set_confirmed": 3 <= len(images) <= 4,
                    "safe_unsafe_pair_confirmed": False,
                    "source_and_license_confirmed": False,
                    "reviewer_ids": [],
                },
            }
        )
    return records


def benign_candidates() -> list[dict[str, Any]]:
    records = []
    for index, source in enumerate(load(BENIGN), start=1):
        images = unique_images(source["user_turns"])
        records.append(
            {
                "schema_version": "4.0.0-draft",
                "seed_id": f"V3B-CAL-{index:02d}",
                "status": "source_candidate",
                "split": "calibration",
                "scene_type": "benign",
                "benign_subcategory": BENIGN_SUBCATEGORIES[index - 1],
                "topic": "TO_SUMMARIZE_FROM_SOURCE_DIALOGUE",
                "independence_rationale": "TO_REWRITE_AND_AUDIT",
                "source": {
                    "datasets": [source["source_dataset"]],
                    "source_ids": [source["source_id"]],
                    "license": "CC BY-NC 4.0; verify against pinned source manifest",
                    "provenance_notes": f"Imported from {source['seed_id']} as a calibration candidate only.",
                },
                "evidence_packets": evidence_packets(images),
                "dialogue_outline": [turn["content"] for turn in source["user_turns"][:6]],
                "final_request": source["user_turns"][-1]["content"],
                "review": {
                    "independent_scene_confirmed": False,
                    "evidence_set_confirmed": 3 <= len(images) <= 4,
                    "benign_task_confirmed": False,
                    "source_and_license_confirmed": False,
                    "reviewer_ids": [],
                },
            }
        )
    return records


def main() -> None:
    payload = {
        "schema_version": "4.0.0-draft",
        "status": "calibration_candidates_not_approved",
        "harmful": harmful_candidates(),
        "benign": benign_candidates(),
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['harmful'])} harmful and {len(payload['benign'])} benign candidates to {OUTPUT}")


if __name__ == "__main__":
    main()
