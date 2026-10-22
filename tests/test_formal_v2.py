import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "processed" / "formal_v2.jsonl"


class FormalV2DatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]

    def test_scale_and_tracks(self):
        self.assertEqual(len(self.records), 1554)
        self.assertEqual(Counter(item["track"] for item in self.records), {
            "static_visual_anchor": 264, "dynamic_risk_trajectory": 160,
            "benign_multi_image_control": 32, "mmds_breadth_length": 768,
            "mmdu_benign_length": 330,
        })

    def test_breadth_semantic_diversity(self):
        mmds = [item for item in self.records if item["track"] == "mmds_breadth_length"]
        mmdu = [item for item in self.records if item["track"] == "mmdu_benign_length"]
        self.assertEqual(len({item["seed_id"] for item in mmds}), 192)
        self.assertEqual(len({item["seed_id"] for item in mmdu}), 110)
        grouped = defaultdict(set)
        for item in mmds:
            grouped[item["risk_category"]].add(item["seed_id"])
        self.assertEqual({len(value) for value in grouped.values()}, {48})

    def test_length_variants_share_user_trajectory(self):
        grouped = defaultdict(list)
        for item in self.records:
            if item["track"] in {"mmds_breadth_length", "mmdu_benign_length"}:
                grouped[item["seed_id"]].append(item)
        for variants in grouped.values():
            expected = 4 if variants[0]["track"] == "mmds_breadth_length" else 3
            self.assertEqual(len(variants), expected)
            base = variants[0]
            for variant in variants[1:]:
                self.assertEqual(len(base["turns"]), len(variant["turns"]))
                self.assertEqual(
                    [[turn["user"]["images"] for turn in base["turns"]]],
                    [[turn["user"]["images"] for turn in variant["turns"]]],
                )
                self.assertEqual(
                    [turn["user"]["content"].split("\n\n")[-1] for turn in base["turns"]],
                    [turn["user"]["content"].split("\n\n")[-1] for turn in variant["turns"]],
                )

    def test_controlled_lengths_within_tolerance(self):
        for item in self.records:
            target = item["variables"].get("target_context_tokens")
            if target:
                self.assertLessEqual(abs(item["context_stats"]["estimated_tokens"] - target) / target, 0.05)


if __name__ == "__main__":
    unittest.main()
