import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('organize_four_model_results', ROOT / 'scripts/organize_four_model_results.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OrganizationTests(unittest.TestCase):
    def test_reference_echo_is_an_observable_match_not_a_safety_label(self):
        record = {'turns': [{'response': {'source': 'fixed_reference', 'text': 'Noted.'}},
                            {'response': {'source': 'model', 'text': ' noted. '}}]}
        self.assertTrue(module.reference_echo(record))
        record['turns'][-1]['response']['text'] = 'Other answer'
        self.assertFalse(module.reference_echo(record))
        record['turns'][-1]['response']['text'] = 'Noted.'
        record['turns'][0]['response']['source'] = 'model'
        self.assertFalse(module.reference_echo(record))

    def test_conflicting_duplicate_success_is_not_silently_selected(self):
        index = {}
        module.register(index, {'sample_id': 'x', 'source_sha256': 'first'})
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate'):
            module.register(index, {'sample_id': 'x', 'source_sha256': 'second'})
        self.assertEqual(index['x']['source_sha256'], 'first')

    def test_identical_duplicate_is_counted_once(self):
        row = {'sample_id': 'x', 'source_sha256': 'same'}
        index = {}
        self.assertTrue(module.register(index, row))
        self.assertFalse(module.register(index, row))
        self.assertEqual(len(index), 1)

    def test_windows_long_path_reader_keeps_error_record_intact(self):
        output = ROOT / 'outputs'
        output.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output) as folder:
            base = Path(folder).resolve()
            base.relative_to(output.resolve())
            path = base / ('a' * 90) / ('b' * 90) / 'error.json'
            disk = module.diskpath(path)
            disk.parent.mkdir(parents=True)
            try:
                disk.write_bytes(b'{"error_type":"OutOfMemoryError","sample_id":"x"}')
                self.assertEqual(module.read(path)['error_type'], 'OutOfMemoryError')
                self.assertEqual(module.sha(path), module.sha(disk))
            finally:
                disk.unlink(missing_ok=True)
                disk.parent.rmdir()
                disk.parent.parent.rmdir()


if __name__ == '__main__':
    unittest.main()
