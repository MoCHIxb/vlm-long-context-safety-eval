import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "processed" / "pilot_v1.jsonl"


class PilotDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]

    def test_expected_size(self):
        self.assertEqual(len(self.records), 192)

    def test_balanced_labels_and_categories(self):
        self.assertEqual(Counter(item["label"] for item in self.records), {"safe": 96, "unsafe": 96})
        self.assertEqual(set(Counter(item["risk_category"] for item in self.records).values()), {48})

    def test_counterfactual_pairs_share_prefix(self):
        pairs = defaultdict(list)
        for item in self.records:
            pairs[item["pair_id"]].append(item)
        self.assertEqual(len(pairs), 96)
        for pair in pairs.values():
            self.assertEqual({item["label"] for item in pair}, {"safe", "unsafe"})
            safe = next(item for item in pair if item["label"] == "safe")
            unsafe = next(item for item in pair if item["label"] == "unsafe")
            self.assertEqual(safe["turns"][:-1], unsafe["turns"][:-1])

    def test_text_only_samples_do_not_reference_images(self):
        visual_phrases = ("image", "shown", "visible", "attached")
        for item in self.records:
            if item["variables"]["modality_relation"] != "text_only":
                continue
            self.assertTrue(all(not turn["user"]["images"] for turn in item["turns"]))
            final = item["turns"][-1]["user"]["content"].lower()
            self.assertFalse(any(phrase in final for phrase in visual_phrases), item["sample_id"])


if __name__ == "__main__":
    unittest.main()

