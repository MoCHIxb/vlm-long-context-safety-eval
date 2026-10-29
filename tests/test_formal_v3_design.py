import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "formal_v3.json"
TAXONOMY = ROOT / "configs" / "formal_v3_taxonomy.json"
CANDIDATES = ROOT / "data" / "seeds" / "formal_v3_calibration_candidates.json"
FULL_BANK = ROOT / "data" / "seeds" / "formal_v3_seed_bank.json"
VALIDATION = ROOT / "documentation" / "reports" / "formal_v3_validation.json"


class FormalV3DesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        cls.candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
        cls.full_bank = json.loads(FULL_BANK.read_text(encoding="utf-8"))
        cls.validation = json.loads(VALIDATION.read_text(encoding="utf-8"))

    def test_expected_size_is_derived_from_seed_level_design(self):
        harmful = 80 * 12 * 2 * 2
        benign = 64 * 3 * 2
        self.assertEqual(self.config["expected_sizes"]["harmful_trajectories"], harmful)
        self.assertEqual(self.config["expected_sizes"]["benign_trajectories"], benign)
        self.assertEqual(self.config["expected_sizes"]["total_trajectories"], harmful + benign)
        self.assertEqual(self.config["expected_sizes"]["independent_semantic_seeds"], 144)

    def test_model_identity_is_not_a_dataset_factor(self):
        factor_names = {profile["factor_under_test"] for profile in self.config["harmful_condition_profiles"]}
        self.assertNotIn("model", factor_names)
        self.assertIn("Model identity is not a dataset factor", self.config["design_principle"])

    def test_primary_visual_schedule_has_two_matched_levels(self):
        schedules = [item["id"] for item in self.config["visual_evidence_schedules"]]
        self.assertEqual(schedules, ["static_initial_bundle", "dynamic_incremental"])
        self.assertFalse(self.config["diagnostic_visual_schedule"]["include_in_primary_factor"])

    def test_taxonomy_has_balanced_targets(self):
        self.assertEqual(set(self.taxonomy["harmful"]), set(self.config["risk_categories"]))
        self.assertTrue(all(len(values) == 4 for values in self.taxonomy["harmful"].values()))
        self.assertEqual(len(self.taxonomy["benign"]), 8)

    def test_calibration_candidates_are_structurally_balanced_but_unapproved(self):
        harmful = self.candidates["harmful"]
        benign = self.candidates["benign"]
        self.assertEqual(len(harmful), 8)
        self.assertEqual(len(benign), 8)
        self.assertEqual(Counter(item["risk_category"] for item in harmful), {
            category: 2 for category in self.config["risk_categories"]
        })
        for item in harmful:
            self.assertIn(len(item["evidence_packets"]), {3, 4})
            self.assertIn(item["risk_subcategory"], self.taxonomy["harmful"][item["risk_category"]])
            self.assertNotEqual(item["status"], "approved")
        for item in benign:
            self.assertIn(len(item["evidence_packets"]), {2, 3, 4})
            self.assertIn(item["benign_subcategory"], self.taxonomy["benign"])
            self.assertNotEqual(item["status"], "approved")

    def test_full_seed_bank_reaches_independent_scene_targets(self):
        self.assertEqual(len(self.full_bank["harmful"]), 80)
        self.assertEqual(len(self.full_bank["benign"]), 64)
        self.assertEqual(Counter(item["risk_category"] for item in self.full_bank["harmful"]), {
            category: 20 for category in self.config["risk_categories"]
        })
        self.assertTrue(all(item["status"] == "machine_constructed_unreviewed" for item in self.full_bank["harmful"] + self.full_bank["benign"]))

    def test_materialized_dataset_passes_pairing_and_length_validation(self):
        self.assertEqual(self.validation["status"], "structurally_valid_machine_constructed_unreviewed")
        self.assertEqual(self.validation["dataset"]["trajectory_count"], 4224)
        self.assertEqual(self.validation["dataset"]["safe_unsafe_pair_count"], 1920)
        self.assertEqual(self.validation["dataset"]["schedule_pair_count"], 2112)
        self.assertEqual(self.validation["seed_bank"]["cross_seed_image_reuse"], 0)
        self.assertLessEqual(self.validation["dataset"]["max_relative_token_deviation"], 0.02)
        self.assertFalse(self.validation["human_review"]["completed"])


if __name__ == "__main__":
    unittest.main()
