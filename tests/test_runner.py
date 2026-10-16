import json
import tempfile
import unittest
from pathlib import Path

from longvision_eval.dataset import load_jsonl, select_records
from longvision_eval.models.mock import MockAdapter
from longvision_eval.models.base import GenerationResult
from longvision_eval.models.qwen_transformers import QwenTransformersAdapter
from longvision_eval.runner import run_record


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "processed" / "pilot_v2.jsonl"


class RunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_jsonl(DATASET)

    def test_select_pair(self):
        ids = {"DYN-MD80-D01-safe", "DYN-MD80-D01-unsafe"}
        selected = select_records(self.records, sample_ids=ids)
        self.assertEqual({record["sample_id"] for record in selected}, ids)

    def test_mock_runs_all_turns(self):
        record = next(item for item in self.records if item["sample_id"] == "DYN-MD80-D01-safe")
        result = run_record(record, MockAdapter({"model_id": "mock"}), {}, ROOT, "interactive")
        self.assertEqual(len(result["turns"]), 4)
        self.assertTrue(all(turn["response"]["source"] == "model" for turn in result["turns"]))
        self.assertTrue(all(turn["response"]["text"].startswith("MOCK_RESPONSE") for turn in result["turns"]))

    def test_adapter_exposes_runtime_metadata(self):
        adapter = MockAdapter({"model_id": "mock", "adapter": "mock"})
        self.assertEqual(adapter.runtime_info(), {"adapter": "mock"})

    def test_generation_result_serializes_truncation_flag(self):
        result = GenerationResult(text="partial", output_tokens=32, truncated=True)
        self.assertTrue(result.to_dict()["truncated"])

    def test_fixed_reference_only_generates_final_turn(self):
        record = next(item for item in self.records if item["sample_id"] == "BEN-MU56-T4-continuation")
        result = run_record(record, MockAdapter({"model_id": "mock"}), {}, ROOT, "fixed_reference")
        self.assertEqual([turn["response"]["source"] for turn in result["turns"]], [
            "fixed_reference", "fixed_reference", "fixed_reference", "model"
        ])

    def test_qwen_uses_windows_local_paths_instead_of_file_uris(self):
        image = ROOT / "data" / "raw" / "images" / "mmds" / "215.jpg"
        converted = QwenTransformersAdapter._qwen_messages(
            [{"role": "user", "content": [{"type": "image", "path": str(image)}, {"type": "text", "text": "test"}]}]
        )
        value = converted[0]["content"][0]["image"]
        self.assertTrue(Path(value).is_absolute())
        self.assertFalse(value.startswith("file:"))


if __name__ == "__main__":
    unittest.main()
