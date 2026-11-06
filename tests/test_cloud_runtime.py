import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cloud_runtime', ROOT / 'scripts/cloud_runtime.py')
cloud = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloud)


class CloudRuntimeTests(unittest.TestCase):
    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            cloud.safe_path(ROOT, '../outside')

    def test_bad_download_cannot_replace_target(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'asset'
            with self.assertRaises(ValueError):
                cloud.checked_copy(io.BytesIO(b'invalid'), target, hashlib.sha256(b'valid').hexdigest())
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix('.part').exists())

    def test_cloud_configuration_keeps_experiment_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'configs', root / 'configs')
            shutil.copytree(ROOT / 'src', root / 'src')
            with patch.object(cloud, 'ROOT', root):
                path = cloud.make_plan(['qwen3vl8b', 'llava7b'])
                plan = cloud.load(path)
                self.assertEqual([m['key'] for m in plan['models']], ['qwen3vl8b', 'llava7b'])
                self.assertEqual(plan['total_formal_samples'], 9728)
                self.assertTrue(plan['serial_models'])
                original = cloud.load(root / cloud.BASE_PLAN)['models'][1]
                before = cloud.load(root / original['formal'])
                after = cloud.load(root / plan['models'][0]['formal'])
                for key in ('generation', 'history_mode', 'expected_dataset_sha256', 'expected_code_sha256', 'model_config'):
                    self.assertEqual(before[key], after[key])
                self.assertTrue(after['run_id'].endswith('-cloud'))
                with self.assertRaises(ValueError):
                    cloud.make_plan(['qwen3vl8b', 'qwen3vl8b'])

    def test_clean_snapshot_restore_matches_frozen_shards(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for path in (cloud.MANIFEST, 'data/releases/formal_v3_18turn_runtime.zip',
                         'data/processed/formal_v3_18turn_shards/manifest.json'):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / path, target)
            with patch.object(cloud, 'ROOT', root):
                cloud.restore()
                manifest = cloud.load(root / cloud.MANIFEST)
                self.assertEqual(cloud.sha(root / manifest['dataset_path']), manifest['dataset_sha256'])
                # A second restore is safe and does not replace matching frozen files.
                cloud.restore()


if __name__ == '__main__':
    unittest.main()
