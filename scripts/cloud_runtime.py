"""Restore the frozen dataset, fetch checked images, and select serial cloud models."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('qwen25vl7b', 'qwen3vl8b', 'llava7b', 'gemma3_12b')
BASE_PLAN = 'configs/runs/formal_v3_18turn/queue-ffd78bcc-ad9fe617-g1024.json'
MANIFEST = 'configs/cloud/runtime_manifest.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Path is outside the intended directory')
    return target


def checked_copy(source, target, expected):
    if target.exists():
        if sha(target) != expected:
            raise ValueError('Existing file has a different fingerprint: ' + str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.part')
    with temporary.open('wb') as dest:
        shutil.copyfileobj(source, dest)
    if sha(temporary) != expected:
        temporary.unlink()
        raise ValueError('Downloaded/restored file checksum mismatch: ' + str(target))
    temporary.replace(target)


def restore():
    manifest = load(ROOT / MANIFEST)
    archive = ROOT / manifest['snapshot']['path']
    if sha(archive) != manifest['snapshot']['sha256']:
        raise ValueError('Runtime snapshot checksum mismatch')
    with zipfile.ZipFile(archive) as bundle:
        for entry in manifest['snapshot']['files']:
            with bundle.open(entry['path']) as stream:
                checked_copy(stream, safe_path(ROOT, entry['path']), entry['sha256'])
    # Recreate deterministic category shards from the exact frozen JSONL bytes.
    shard_manifest = load(ROOT / 'data/processed/formal_v3_18turn_shards/manifest.json')
    rows = {}
    dataset = ROOT / manifest['dataset_path']
    with dataset.open('rb') as stream:
        for line in stream:
            item = json.loads(line)
            category = item['risk_category'] if item['track'] == 'harmful_controlled' else 'benign'
            rows.setdefault(category, []).append(line)
    for entry in shard_manifest['shards']:
        target = safe_path(ROOT, entry['path'])
        if target.exists() and sha(target) == entry['sha256']:
            continue
        if target.exists():
            raise ValueError('Existing category shard differs; refusing to replace it')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('wb') as raw:
            with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
                zipped.writelines(rows[target.name.removesuffix('.jsonl.gz')])
        if sha(target) != entry['sha256']:
            target.unlink()
            raise ValueError('Recreated shard checksum mismatch')
    print('Frozen dataset and sampling plan restored; category shard checksums verified.')


def prepare_assets():
    manifest = load(ROOT / MANIFEST)
    archives = {v['key']: v for v in manifest['image_archives']}
    pending = {}
    for image in manifest['images']:
        target = safe_path(ROOT, image['path'])
        if target.exists():
            if sha(target) != image['sha256']:
                raise ValueError('Existing image checksum mismatch: ' + image['path'])
        else:
            pending.setdefault(image['archive'], []).append(image)
    for key, images in pending.items():
        info = archives[key]
        target = safe_path(ROOT / '.cache/cloud_sources', key + '.zip')
        if not target.exists():
            print('Downloading public image archive: ' + key, flush=True)
            # Checksums pin the exact source even if the upstream branch changes.
            with urllib.request.urlopen(info['url'], timeout=120) as source:
                checked_copy(source, target, info['sha256'])
        if sha(target) != info['sha256']:
            raise ValueError('Image archive checksum mismatch: ' + key)
        with zipfile.ZipFile(target) as archive:
            for image in images:
                with archive.open(image['member']) as source:
                    checked_copy(source, safe_path(ROOT, image['path']), image['sha256'])
    print('Verified ' + str(len(manifest['images'])) + ' required images.')


def make_plan(keys):
    if len(keys) != len(set(keys)) or set(keys) - set(KEYS):
        raise ValueError('Cloud model selection must contain distinct supported keys')
    plan = load(ROOT / BASE_PLAN)
    selected = []
    directory = ROOT / 'outputs/cloud_configs'
    for key in keys:
        original = next(m for m in plan['models'] if m['key'] == key)
        item = dict(original)
        for stage in ('gate', 'formal'):
            config = load(ROOT / original[stage])
            for path, expected in config['expected_code_sha256'].items():
                if sha(ROOT / path) != expected:
                    raise ValueError('Frozen inference code differs: ' + path)
            config['run_id'] += '-cloud'
            config['execution_site'] = 'cloud'
            path = directory / (config['run_id'] + '.json')
            if path.exists() and load(path) != config:
                raise ValueError('Existing cloud configuration differs; use a new run version')
            save(path, config)
            item[stage] = path.relative_to(ROOT).as_posix()
        selected.append(item)
    plan.update(models=selected, total_formal_samples=len(keys) * plan['sample_count_per_model'],
                execution_site='cloud', local_qwen_run_not_transferred=True)
    path = directory / ('queue-' + '-'.join(keys) + '.json')
    save(path, plan)
    return path


def check():
    import torch
    packages = ('torch', 'torchvision', 'transformers', 'accelerate', 'bitsandbytes',
                'huggingface-hub', 'pillow', 'safetensors', 'tokenizers', 'numpy')
    report = {'python': platform.python_version(), 'platform': platform.platform(),
              'packages': {p: importlib.metadata.version(p) for p in packages},
              'cuda_available': torch.cuda.is_available(), 'torch_cuda': torch.version.cuda}
    if torch.cuda.is_available():
        report.update(gpu=torch.cuda.get_device_name(0), bf16_supported=torch.cuda.is_bf16_supported(),
                      gpu_memory_bytes=torch.cuda.get_device_properties(0).total_memory)
    save(ROOT / 'outputs/cloud_environment/environment.json', report)
    print(json.dumps(report, indent=2))
    if not report['cuda_available'] or not report.get('bf16_supported'):
        raise SystemExit('An NVIDIA CUDA GPU with BF16 support is required; no CPU fallback.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'download', 'plan', 'run', 'check'))
    parser.add_argument('--model', action='append', choices=KEYS)
    parser.add_argument('--include-gated', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    env = os.environ.copy()
    env.update(PYTHONPATH=str(ROOT / 'src'), HF_HOME=os.environ.get('HF_HOME', str(ROOT / '.cache/huggingface')),
               HF_HUB_DISABLE_TELEMETRY='1', HF_HUB_DISABLE_XET='1', PYTHONUTF8='1')
    keys = args.model or ['qwen3vl8b']
    if args.action == 'check':
        check()
    elif args.action == 'prepare':
        restore()
        prepare_assets()
        subprocess.run([sys.executable, 'scripts/validate_formal_v3_18turn.py'], env=env, check=True)
    elif args.action == 'download':
        if 'gemma3_12b' in keys and not args.include_gated:
            parser.error('Gemma requires server-side HF login and --include-gated')
        env.update(HF_HUB_OFFLINE='0', TRANSFORMERS_OFFLINE='0')
        for key in keys:
            subprocess.run([sys.executable, 'scripts/prepare_open_models.py', '--model', key, '--download',
                            '--processor-check', *(['--include-gated'] if args.include_gated else [])],
                           env=env, check=True)
            report = load(ROOT / 'outputs/model_deployment' / (key + '.json'))
            if not report.get('inventory', {}).get('weights_complete') or not report.get('processor_check', {}).get('passed'):
                raise SystemExit('Model preparation incomplete; inspect deployment report: ' + key)
    else:
        path = make_plan(keys)
        print('Cloud plan: ' + path.relative_to(ROOT).as_posix())
        if args.action == 'run':
            # Cheap checks before starting a model, then the existing serial gate/full runner.
            manifest = load(ROOT / MANIFEST)
            if sha(ROOT / manifest['dataset_path']) != manifest['dataset_sha256']:
                raise ValueError('Frozen dataset fingerprint differs')
            for image in manifest['images']:
                if sha(safe_path(ROOT, image['path'])) != image['sha256']:
                    raise ValueError('Image fingerprint differs: ' + image['path'])
            env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
            subprocess.run([sys.executable, 'scripts/run_formal_v3_18turn_queue.py',
                            '--plan', path.relative_to(ROOT).as_posix()], env=env, check=True)


if __name__ == '__main__':
    main()
