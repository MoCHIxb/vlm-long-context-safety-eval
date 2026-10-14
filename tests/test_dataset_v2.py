import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "processed" / "pilot_v2.jsonl"


class PilotV2DatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]

    def test_expected_size_and_tracks(self):
        self.assertEqual(len(self.records), 160)
        self.assertEqual(
            Counter(item["track"] for item in self.records),
            {"static_visual_anchor": 64, "dynamic_risk_trajectory": 64, "benign_multi_image_control": 32},
        )

    def test_dynamic_pairs_share_prefix_and_images(self):
        pairs = defaultdict(list)
        for item in self.records:
            if item["track"] == "dynamic_risk_trajectory":
                pairs[item["pair_id"]].append(item)
        self.assertEqual(len(pairs), 32)
        for pair in pairs.values():
            self.assertEqual({item["label"] for item in pair}, {"safe", "unsafe"})
            safe = next(item for item in pair if item["label"] == "safe")
            unsafe = next(item for item in pair if item["label"] == "unsafe")
            self.assertEqual(safe["turns"][:-1], unsafe["turns"][:-1])
            self.assertEqual(safe["turns"][-1]["user"]["images"], unsafe["turns"][-1]["user"]["images"])

    def test_dynamic_tracks_have_cross_turn_visual_change(self):
        for item in self.records:
            if item["track"] != "dynamic_risk_trajectory":
                continue
            image_turns = [turn for turn in item["turns"] if turn["user"]["images"]]
            images = {image for turn in image_turns for image in turn["user"]["images"]}
            self.assertGreaterEqual(len(image_turns), 2, item["sample_id"])
            self.assertGreaterEqual(len(images), 2, item["sample_id"])

    def test_neutral_turns_after_risk_preserve_history_state(self):
        for item in self.records:
            if item["track"] != "dynamic_risk_trajectory":
                continue
            risk_seen = False
            for turn in item["turns"][:-1]:
                state = turn["gold"]["risk_state"]
                if state in {"latent_risk", "escalating_risk"}:
                    risk_seen = True
                if risk_seen and turn["gold"]["evidence_role"] == "history_retention_control":
                    self.assertEqual(state, "risk_carryover", item["sample_id"])

    def test_static_track_uses_one_visual_anchor(self):
        for item in self.records:
            if item["track"] != "static_visual_anchor":
                continue
            images = {image for turn in item["turns"] for image in turn["user"]["images"]}
            self.assertEqual(len(images), 1, item["sample_id"])

    def test_benign_track_is_safe_and_multi_image(self):
        for item in self.records:
            if item["track"] != "benign_multi_image_control":
                continue
            self.assertEqual(item["label"], "safe")
            images = {image for turn in item["turns"] for image in turn["user"]["images"]}
            self.assertGreaterEqual(len(images), 2, item["sample_id"])

    def test_all_referenced_images_exist(self):
        for item in self.records:
            for turn in item["turns"]:
                for image in turn["user"]["images"]:
                    self.assertTrue((ROOT / image).is_file(), f"{item['sample_id']}: {image}")


if __name__ == "__main__":
    unittest.main()
