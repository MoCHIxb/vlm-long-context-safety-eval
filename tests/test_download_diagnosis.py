import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('download_diagnosis',
    Path(__file__).resolve().parents[1] / 'scripts/diagnose_hf_download.py')
diagnosis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnosis)


class DownloadDiagnosisTests(unittest.TestCase):
    def test_redacts_urls_tokens_and_environment_secrets(self):
        secret = 'hf_' + 'SyntheticPrivateValue' * 2
        with patch.dict(os.environ, {'HF_TOKEN': secret, 'CUSTOM_API_KEY': 'private-example-value'}):
            message = diagnosis.redact(secret + ' Bearer private-access-value '
                                       + 'https://user:password@example.test/file?signature=private '
                                       + 'private-example-value')
        for value in (secret, 'private-access-value', 'user:password', 'signature=private', 'private-example-value'):
            self.assertNotIn(value, message)

    def test_preserves_typeerror_and_context_status_without_source_lines(self):
        try:
            try:
                raise RuntimeError('upstream failure')
            except RuntimeError as cause:
                cause.response = type('Response', (), {'status_code': 403})()
                raise TypeError('expected bytes, got str') from cause
        except TypeError as error:
            report = diagnosis.error_report(error)
        self.assertEqual(report[0]['type'], 'TypeError')
        self.assertIn('expected bytes', report[0]['message'])
        self.assertEqual(report[1]['http_status'], 403)
        self.assertNotIn('source', report[0]['frames'][0])


if __name__ == '__main__':
    unittest.main()
