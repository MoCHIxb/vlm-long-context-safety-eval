"""Diagnose one tiny pinned config download, without weights, GPU, or token output."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import re
import traceback

ROOT = Path(__file__).resolve().parents[1]


def redact(message):
    text = str(message)
    for name, value in os.environ.items():
        if len(value) >= 8 and any(word in name.upper() for word in ('TOKEN', 'SECRET', 'PASSWORD', 'API_KEY')):
            text = text.replace(value, '[REDACTED]')
    text = re.sub(r'https?://[^\s\x27\x22<>]+', '[URL REDACTED]', text)
    text = re.sub(r'\b(?:hf_|gh[pousr]_|sk-)[A-Za-z0-9_-]{8,}', '[TOKEN REDACTED]', text)
    text = re.sub(r'(?i)Bearer\s+[^\s\x27\x22,;]+', 'Bearer [REDACTED]', text)
    return text[:1500]


def error_report(error):
    chain, seen = [], set()
    while error is not None and id(error) not in seen and len(chain) < 6:
        seen.add(id(error))
        response = getattr(error, 'response', None)
        chain.append({'type': type(error).__name__, 'message': redact(error),
                      'http_status': getattr(response, 'status_code', None),
                      'frames': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                                 for f in traceback.extract_tb(error.__traceback__)]})
        error = error.__cause__ or error.__context__
    return chain


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='llava7b', choices=('llava7b', 'gemma3_12b'))
    parser.add_argument('--disable-progress', action='store_true', help='Second probe to isolate progress-bar failures')
    args = parser.parse_args()
    os.environ['HF_HOME'] = str(ROOT / '.cache/huggingface')
    os.environ['HF_HUB_OFFLINE'] = '0'
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '30'
    os.environ['HF_HUB_ETAG_TIMEOUT'] = '15'
    if args.disable_progress:
        os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    models = json.loads((ROOT / 'configs/deployment/open_models.json').read_text(encoding='utf-8'))['models']
    config = next(m for m in models if m['key'] == args.model)
    versions = {}
    for name in ('huggingface-hub', 'httpx2', 'httpcore2', 'Brotli', 'brotlicffi', 'tqdm', 'rich', 'anyio', 'truststore'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'not installed'
    report = {'model': args.model, 'revision': config['revision'], 'file': 'config.json',
              'packages': versions, 'disable_progress_requested': args.disable_progress,
              'proxy_env_present': {key: bool(os.environ.get(key)) for key in
                                    ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')},
              'gpu_used': False, 'weight_files_requested': 0}
    try:
        from huggingface_hub import hf_hub_download
        path = Path(hf_hub_download(config['model_name'], 'config.json', revision=config['revision']))
        report.update(passed=True, downloaded_bytes=path.stat().st_size)
    except Exception as error:
        report.update(passed=False, errors=error_report(error))
    output = ROOT / 'outputs/model_deployment' / ('download_diagnosis_' + args.model
                                                + ('_no_progress' if args.disable_progress else '') + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
