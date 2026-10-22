import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "processed" / "formal_v1.jsonl"


class FormalV1DatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]

    def test_expected_size_tracks_and_labels(self):
        self.assertEqual(len(self.records), 456)
        self.assertEqual(
            Counter(item["track"] for item in self.records),
            {"static_visual_anchor": 264, "dynamic_risk_trajectory": 160, "benign_multi_image_control": 32},
        )
        self.assertEqual(Counter(item["label"] for item in self.records), {"safe": 244, "unsafe": 212})

    def test_counterfactual_pairs_share_prefix_and_final_images(self):
        pairs = defaultdict(list)
        for item in self.records:
            if item["pair_id"]:
                pairs[item["pair_id"]].append(item)
        self.assertEqual(len(pairs), 212)
        for pair in pairs.values():
            self.assertEqual({item["label"] for item in pair}, {"safe", "unsafe"})
            safe = next(item for item in pair if item["label"] == "safe")
            unsafe = next(item for item in pair if item["label"] == "unsafe")
            self.assertEqual(safe["turns"][:-1], unsafe["turns"][:-1])
            self.assertEqual(safe["turns"][-1]["user"]["images"], unsafe["turns"][-1]["user"]["images"])

    def test_each_controlled_condition_declares_reference_and_factor(self):
        for item in self.records:
            self.assertIn("factor_under_test", item["variables"])
            self.assertIn("reference_condition_id", item["variables"])

    def test_final_bundle_condition_moves_all_images_to_final_turn(self):
        records = [item for item in self.records if item["condition_id"] == "FD09"]
        self.assertEqual(len(records), 16)
        for item in records:
            image_turns = [turn for turn in item["turns"] if turn["user"]["images"]]
            self.assertEqual(len(image_turns), 1)
            self.assertEqual(image_turns[0]["turn_index"], len(item["turns"]))
            self.assertGreaterEqual(len(image_turns[0]["user"]["images"]), 2)

    def test_risk_categories_are_balanced(self):
        counts = Counter(
            item["risk_category"] for item in self.records if item["track"] != "benign_multi_image_control"
        )
        self.assertEqual(len(set(counts.values())), 1)
        self.assertEqual(set(counts.values()), {106})


if __name__ == "__main__":
    unittest.main()
