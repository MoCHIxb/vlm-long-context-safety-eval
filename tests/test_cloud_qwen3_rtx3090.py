import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('qwen3_cloud_profile', ROOT / 'scripts/cloud_runtime_rtx3090.py')
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)
PROFILE = 'configs/cloud/rtx3090_qwen3.json'


class Qwen3CloudTests(unittest.TestCase):
    def test_only_qwen3_same_frozen_controls_in_separate_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'configs', root / 'configs')
            shutil.copytree(ROOT / 'src', root / 'src')
            with patch.object(runtime, 'ROOT', root), patch.object(runtime, 'PROFILE', PROFILE):
                plan = runtime.shared.load(runtime.make_plan())
                self.assertEqual([m['key'] for m in plan['models']], ['qwen3vl8b'])
                self.assertEqual(plan['total_formal_samples'], 4864)
                original_plan = runtime.shared.load(root / runtime.load_profile()['base_plan'])
                original = next(m for m in original_plan['models'] if m['key'] == 'qwen3vl8b')
                for stage in ('gate', 'formal'):
                    before = runtime.shared.load(root / original[stage])
                    after = runtime.shared.load(root / plan['models'][0][stage])
                    for field in ('generation', 'history_mode', 'model_config', 'expected_dataset_sha256',
                                  'expected_code_sha256', 'sample_ids'):
                        self.assertEqual(before.get(field), after.get(field))
                    self.assertEqual(after['output_dir'], 'outputs/cloud_rtx3090_qwen3_runs')
                    self.assertTrue(after['run_id'].endswith('-rtx3090-qwen3-t2121-py312'))

    def test_qwen3_profile_rejects_other_models(self):
        with patch.object(runtime, 'PROFILE', PROFILE):
            for key in ('qwen25vl7b', 'llava7b', 'gemma3_12b'):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    runtime.make_plan([key])

    def test_default_llava_gemma_profile_is_unchanged(self):
        self.assertEqual(runtime.PROFILE, 'configs/cloud/rtx3090_llava_gemma.json')
        self.assertEqual(runtime.load_profile()['models'], ['llava7b', 'gemma3_12b'])


if __name__ == '__main__':
    unittest.main()
