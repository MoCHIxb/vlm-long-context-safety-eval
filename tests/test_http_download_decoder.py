import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('http_download_check',
    Path(__file__).resolve().parents[1] / 'scripts/check_http_download.py')
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


class HTTPDecoderTests(unittest.TestCase):
    def test_old_brotli_keyword_failure_has_targeted_remedy(self):
        class BrokenDecoder:
            def decode(self, data):
                raise TypeError('process() takes no keyword arguments')
        modules = {'brotli': SimpleNamespace(compress=lambda data: data),
                   'httpx2._decoders': SimpleNamespace(BrotliDecoder=BrokenDecoder)}
        with patch.dict(sys.modules, modules), self.assertRaisesRegex(RuntimeError, 'Brotli==1.2.0'):
            check.check_brotli_decoder()

    def test_roundtrip_checks_actual_decoded_content(self):
        class Decoder:
            def decode(self, data):
                return iter([data])
            def flush(self):
                return iter([])
        modules = {'brotli': SimpleNamespace(compress=lambda data: data),
                   'httpx2._decoders': SimpleNamespace(BrotliDecoder=Decoder)}
        with patch.dict(sys.modules, modules), patch.object(check.importlib.metadata, 'version', return_value='test'):
            report = check.check_brotli_decoder()
        self.assertTrue(report['passed'])
        self.assertEqual(report['network_requests'], 0)

    def test_corrupt_decode_is_rejected(self):
        class Decoder:
            def decode(self, data):
                return iter([b'different'])
            def flush(self):
                return iter([])
        modules = {'brotli': SimpleNamespace(compress=lambda data: data),
                   'httpx2._decoders': SimpleNamespace(BrotliDecoder=Decoder)}
        with patch.dict(sys.modules, modules), self.assertRaises(RuntimeError):
            check.check_brotli_decoder()


if __name__ == '__main__':
    unittest.main()
