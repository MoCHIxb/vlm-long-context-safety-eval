import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('cloud3090', ROOT / 'scripts/cloud_runtime_rtx3090.py')
cloud = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloud)


class CloudRTX3090Tests(unittest.TestCase):
    def test_default_queue_retains_frozen_protocol(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'configs', root / 'configs')
            shutil.copytree(ROOT / 'src', root / 'src')
            with patch.object(cloud, 'ROOT', root):
                profile = cloud.load_profile()
                plan = cloud.shared.load(cloud.make_plan())
                self.assertEqual([m['key'] for m in plan['models']], ['llava7b', 'gemma3_12b'])
                self.assertEqual(plan['total_formal_samples'], 9728)
                self.assertTrue(plan['serial_models'])
                original = cloud.shared.load(root / profile['base_plan'])
                for item in plan['models']:
                    before = next(m for m in original['models'] if m['key'] == item['key'])
                    for stage in ('gate', 'formal'):
                        a = cloud.shared.load(root / before[stage])
                        b = cloud.shared.load(root / item[stage])
                        for field in ('generation', 'history_mode', 'expected_dataset_sha256',
                                      'expected_code_sha256', 'model_config', 'sample_ids'):
                            self.assertEqual(a.get(field), b.get(field))
                        self.assertTrue(b['run_id'].endswith('-rtx3090-t2121-py312'))
                        self.assertEqual(b['output_dir'], 'outputs/cloud_rtx3090_runs')

    def test_invalid_or_duplicate_selection_rejected(self):
        for keys in ([], ['qwen3vl8b'], ['llava7b', 'llava7b']):
            with self.assertRaises(ValueError):
                cloud.make_plan(keys)

    def test_environment_mismatch_is_not_silently_accepted(self):
        profile = cloud.load_profile()
        report = {'system': 'Linux', 'python_major_minor': [3, 12], 'torch_version': '2.12.1',
                  'torchvision_version': '0.27.1', 'torch_cuda': '13.0', 'visible_gpus': 1,
                  'gpu': 'NVIDIA GeForce RTX 3090', 'cuda_available': True,
                  'bf16_supported': True, 'gpu_memory_bytes': 24 * 1024**3}
        cloud.validate_environment(report, profile)
        for field, wrong in [('torch_version', '2.14.1'), ('torch_cuda', '12.8'),
                             ('python_major_minor', [3, 14]), ('gpu', 'NVIDIA GeForce RTX 4090'),
                             ('visible_gpus', 2), ('bf16_supported', False)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                cloud.validate_environment({**report, field: wrong}, profile)

    def test_changed_existing_configuration_refuses_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'configs', root / 'configs')
            shutil.copytree(ROOT / 'src', root / 'src')
            with patch.object(cloud, 'ROOT', root):
                plan = cloud.shared.load(cloud.make_plan(['llava7b']))
                path = root / plan['models'][0]['formal']
                config = cloud.shared.load(path)
                config['generation']['max_new_tokens'] = 128
                cloud.shared.save(path, config)
                with self.assertRaises(ValueError):
                    cloud.make_plan(['llava7b'])


if __name__ == '__main__':
    unittest.main()
