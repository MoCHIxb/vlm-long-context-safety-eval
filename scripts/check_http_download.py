"""Offline check for the Brotli decoder used by Hugging Face's HTTP transport."""
from __future__ import annotations

import importlib.metadata


def check_brotli_decoder():
    try:
        import brotli
        from httpx2._decoders import BrotliDecoder
        original = b'Benign download decoder compatibility check.\n' * 32
        compressed = brotli.compress(original)
        decoder = BrotliDecoder()
        restored = b''.join(decoder.decode(compressed)) + b''.join(decoder.flush())
        if restored != original:
            raise ValueError('Brotli response roundtrip differed')
    except (ImportError, TypeError, ValueError) as error:
        raise RuntimeError(
            'HTTP Brotli decoder is incompatible. In the RTX3090 venv run: '
            ".cache/venvs/rtx3090/bin/python -m pip install --upgrade 'Brotli==1.2.0'"
        ) from error
    return {'passed': True, 'network_requests': 0,
            'brotli': importlib.metadata.version('Brotli'),
            'httpx2': importlib.metadata.version('httpx2'),
            'decoded_bytes': len(restored)}


if __name__ == '__main__':
    import json
    print(json.dumps(check_brotli_decoder(), indent=2))
