import json
import tempfile
import unittest
from pathlib import Path

from longvision_eval.dataset import load_jsonl, select_records
from longvision_eval.models.mock import MockAdapter
from longvision_eval.models.base import GenerationResult, generation_options
from longvision_eval.models.qwen_transformers import QwenTransformersAdapter
from longvision_eval.models.smolvlm_transformers import SmolVLMTransformersAdapter
from longvision_eval.runner import run_record, user_message, write_json_atomic


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

    def test_select_condition(self):
        selected = select_records(self.records, condition_ids={"D01"})
        self.assertTrue(selected)
        self.assertEqual({record["condition_id"] for record in selected}, {"D01"})

    def test_mock_runs_all_turns(self):
        record = next(item for item in self.records if item["sample_id"] == "DYN-MD80-D01-safe")
        result = run_record(record, MockAdapter({"model_id": "mock"}), {}, ROOT, "interactive")
        self.assertEqual(len(result["turns"]), 4)
        self.assertTrue(all(turn["response"]["source"] == "model" for turn in result["turns"]))
        self.assertTrue(all(turn["response"]["text"].startswith("MOCK_RESPONSE") for turn in result["turns"]))

    def test_system_prompt_is_added_to_model_history(self):
        class RecordingAdapter(MockAdapter):
            def generate(self, messages, generation):
                self.last_messages = messages
                return super().generate(messages, generation)

        record = next(item for item in self.records if item["sample_id"] == "DYN-MD80-D01-safe")
        adapter = RecordingAdapter({"model_id": "mock"})
        run_record(record, adapter, {}, ROOT, "interactive", "Keep answers concise.")
        self.assertEqual(adapter.last_messages[0], {"role": "system", "content": "Keep answers concise."})

    def test_response_instruction_is_appended_to_each_user_turn(self):
        turn = {"user": {"content": "Describe the image.", "images": []}}
        message = user_message(turn, ROOT, "Use no more than 120 English words.")
        self.assertIn("Response constraint", message["content"][-1]["text"])
        self.assertIn("120 English words", message["content"][-1]["text"])

    def test_adapter_exposes_runtime_metadata(self):
        adapter = MockAdapter({"model_id": "mock", "adapter": "mock"})
        self.assertEqual(adapter.runtime_info(), {"adapter": "mock"})

    def test_generation_result_serializes_truncation_flag(self):
        result = GenerationResult(text="partial", output_tokens=32, truncated=True)
        self.assertTrue(result.to_dict()["truncated"])

    def test_shared_generation_options_include_repetition_controls(self):
        options = generation_options(
            {"max_new_tokens": 384, "repetition_penalty": 1.05, "no_repeat_ngram_size": 5},
            default_max_new_tokens=128,
        )
        self.assertEqual(options["repetition_penalty"], 1.05)
        self.assertEqual(options["no_repeat_ngram_size"], 5)

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

    def test_smolvlm_uses_windows_local_paths(self):
        image = ROOT / "data" / "raw" / "images" / "mmds" / "215.jpg"
        converted = SmolVLMTransformersAdapter._smol_messages(
            [{"role": "user", "content": [{"type": "image", "path": str(image)}, {"type": "text", "text": "test"}]}]
        )
        value = converted[0]["content"][0]["path"]
        self.assertTrue(Path(value).is_absolute())

    def test_smolvlm_normalizes_empty_assistant_content(self):
        converted = SmolVLMTransformersAdapter._smol_messages(
            [{"role": "assistant", "content": ""}]
        )
        self.assertEqual(converted[0]["content"], [{"type": "text", "text": ""}])

    def test_atomic_json_write_replaces_target(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            write_json_atomic(path, {"value": 1})
            write_json_atomic(path, {"value": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 2})
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
