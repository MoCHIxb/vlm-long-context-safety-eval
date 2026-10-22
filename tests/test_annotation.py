import json
import tempfile
import unittest
from pathlib import Path

from longvision_eval.annotation import build_annotation_items, compare_annotation_sets, summarize_annotations
from longvision_eval.dataset import load_jsonl
from longvision_eval.run_metrics import summarize_runs


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "processed" / "pilot_v2.jsonl"


def fake_result(record, model_id="test-model", label=None):
    chosen_label = label or record["label"]
    return {
        "sample_id": record["sample_id"],
        "pair_id": record["pair_id"],
        "track": record["track"],
        "label": chosen_label,
        "condition_id": record["condition_id"],
        "risk_category": record["risk_category"],
        "turns": [
            {
                "turn_index": turn["turn_index"],
                "response": {
                    "text": f"answer-{turn['turn_index']}",
                    "input_tokens": 10 * turn["turn_index"],
                    "output_tokens": 5,
                    "truncated": False,
                    "duration_seconds": 0.1,
                    "peak_gpu_memory_mb": 100,
                },
            }
            for turn in record["turns"]
        ],
        "run": {"run_id": "test-run", "model_id": model_id},
    }


class AnnotationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_jsonl(DATASET)

    def test_build_annotation_item_contains_full_dialogue_and_blinded_model(self):
        record = self.records[0]
        items, key = build_annotation_items(self.records, [fake_result(record)], "ann-a")
        self.assertEqual(len(items[0]["dialogue"]), len(record["turns"]))
        self.assertEqual(items[0]["model_alias"], "M01")
        self.assertNotIn("model_id", items[0])
        self.assertEqual(key["model_aliases"]["test-model"], "M01")

    def test_annotation_summary_uses_fixed_denominators(self):
        items = [
            {"response_id": "a", "model_alias": "M01", "gold_sample_label": "unsafe", "annotation": {"outcome": "unsafe_compliance"}},
            {"response_id": "b", "model_alias": "M01", "gold_sample_label": "unsafe", "annotation": {"outcome": "safe_refusal"}},
            {"response_id": "c", "model_alias": "M01", "gold_sample_label": "safe", "annotation": {"outcome": "safe_helpful"}},
            {"response_id": "d", "model_alias": "M01", "gold_sample_label": "safe", "annotation": {"outcome": "over_refusal"}},
        ]
        summary = summarize_annotations(items)
        self.assertEqual(summary["overall"]["attack_success_rate"], 0.5)
        self.assertEqual(summary["overall"]["over_refusal_rate"], 0.5)

    def test_annotation_agreement_reports_kappa_and_disagreements(self):
        first = [
            {"response_id": "a", "annotation": {"outcome": "safe_helpful"}},
            {"response_id": "b", "annotation": {"outcome": "safe_refusal"}},
        ]
        second = [
            {"response_id": "a", "annotation": {"outcome": "safe_helpful"}},
            {"response_id": "b", "annotation": {"outcome": "safe_redirect"}},
        ]
        comparison = compare_annotation_sets(first, second)
        self.assertEqual(comparison["agreement_rate"], 0.5)
        self.assertEqual(comparison["disagreements"][0]["response_id"], "b")

    def test_run_summary_counts_truncation_and_exact_pair_prefix(self):
        safe = next(record for record in self.records if record["sample_id"] == "DYN-MD80-D01-safe")
        unsafe = next(record for record in self.records if record["sample_id"] == "DYN-MD80-D01-unsafe")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "safe.json").write_text(json.dumps(fake_result(safe)), encoding="utf-8")
            (path / "unsafe.json").write_text(json.dumps(fake_result(unsafe)), encoding="utf-8")
            summary = summarize_runs([path])
        self.assertEqual(summary["sample_count"], 2)
        self.assertEqual(summary["exact_shared_prefix_pairs"], 1)
        self.assertEqual(summary["truncated_final_calls"], 0)


if __name__ == "__main__":
    unittest.main()
