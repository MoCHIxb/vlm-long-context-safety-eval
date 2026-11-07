import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from longvision_eval.annotation import result_files
from longvision_eval.models.qwen_transformers import QwenTransformersAdapter

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_open_models", ROOT / "scripts/prepare_open_models.py")
DEPLOY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPLOY)


class ModelDeploymentTest(unittest.TestCase):
    def test_reference_and_system_text_use_structured_blocks(self):
        converted = QwenTransformersAdapter._qwen_messages([
            {"role": "system", "content": "Keep the context."},
            {"role": "assistant", "content": "Earlier reference response."}])
        self.assertEqual(converted[0]["content"], [{"type": "text", "text": "Keep the context."}])
        self.assertEqual(converted[1]["content"], [{"type": "text", "text": "Earlier reference response."}])

    def test_missing_shard_is_not_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("config.json", "tokenizer_config.json", "preprocessor_config.json", "tokenizer.json"):
                (root / name).write_text("{}", encoding="utf-8")
            (root / "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": {"a": "model-00001-of-00002.safetensors",
                                          "b": "model-00002-of-00002.safetensors"}}), encoding="utf-8")
            report = DEPLOY.inspect_snapshot(root)
            self.assertFalse(report["weights_complete"])
            self.assertIn("model-00002-of-00002.safetensors", report["missing_files"])

    def test_empty_weight_index_is_not_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("config.json", "tokenizer_config.json", "preprocessor_config.json", "tokenizer.json"):
                (root / name).write_text("{}", encoding="utf-8")
            (root / "model.safetensors.index.json").write_text('{"weight_map": {}}', encoding="utf-8")
            self.assertFalse(DEPLOY.inspect_snapshot(root)["weights_complete"])

    def test_synthetic_smoke_does_not_load_when_gpu_busy(self):
        from unittest.mock import patch
        import longvision_eval.models
        with patch.object(DEPLOY, "gpu_free_mib", return_value=6000), \
             patch.object(longvision_eval.models, "create_adapter") as factory:
            report = DEPLOY.smoke_check({"minimum_free_gpu_mib": 11000})
            self.assertEqual(report["status"], "waiting_for_gpu")
            factory.assert_not_called()

    def test_run_manifest_is_not_a_sample_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("run_manifest.json", "run_summary.json", "V3B-001.json"):
                (root / name).write_text("{}", encoding="utf-8")
            self.assertEqual([p.name for p in result_files(root)], ["V3B-001.json"])

    def test_pause_and_technical_reports_are_not_sample_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('technical_metrics.json', 'completion_audit.json', 'pause_audit.json',
                         'pause_manifest.json', 'pause_receipt.json', 'V318-synthetic.json'):
                (root / name).write_text('{}', encoding='utf-8')
            self.assertEqual([p.name for p in result_files(root)], ['V318-synthetic.json'])


if __name__ == "__main__":
    unittest.main()
