"""Independent RTX3090 profile; existing cloud scripts/configurations stay unchanged."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import cloud_runtime as shared

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'configs/cloud/rtx3090_llava_gemma.json'


def load_profile():
    return shared.load(ROOT / PROFILE)


def validate_environment(report, profile):
    problems = []
    for field, expected in (('system', profile['system']),
                            ('python_major_minor', profile['python_major_minor']),
                            ('torch_version', profile['torch_version']),
                            ('torchvision_version', profile['torchvision_version']),
                            ('torch_cuda', profile['torch_cuda']),
                            ('visible_gpus', profile['visible_gpus'])):
        if report.get(field) != expected:
            problems.append(field + ': expected ' + str(expected) + ', got ' + str(report.get(field)))
    if not report.get('gpu', '').upper().endswith(profile['gpu_name_suffix'].upper()):
        problems.append('Expected the selected RTX3090 GPU')
    if not report.get('cuda_available') or not report.get('bf16_supported'):
        problems.append('CUDA and BF16 support are required')
    if report.get('gpu_memory_bytes', 0) < 23 * 1024**3:
        problems.append('Expected approximately 24GiB physical GPU memory')
    if problems:
        raise ValueError('; '.join(problems))


def environment_check():
    import torch
    import torchvision
    # Import the actual classes to catch processor/torchvision dependency failures early.
    from transformers import Gemma3ForConditionalGeneration, LlavaOnevisionForConditionalGeneration
    profile = load_profile()
    report = {'system': platform.system(), 'platform': platform.platform(),
              'python': platform.python_version(), 'python_major_minor': list(sys.version_info[:2]),
              'torch_version': torch.__version__.split('+')[0],
              'torchvision_version': torchvision.__version__.split('+')[0],
              'torch_cuda': torch.version.cuda, 'cuda_available': torch.cuda.is_available(),
              'visible_gpus': torch.cuda.device_count(),
              'packages': {p: importlib.metadata.version(p) for p in
                           ('torch', 'torchvision', 'transformers', 'accelerate', 'bitsandbytes',
                            'huggingface-hub', 'pillow', 'safetensors', 'tokenizers', 'numpy')},
              'profile': profile['profile'], 'profile_sha256': shared.sha(ROOT / PROFILE),
              'cpu_logical_count': os.cpu_count(), 'model_classes_importable': True}
    if report['cuda_available']:
        report.update(gpu=torch.cuda.get_device_name(0), bf16_supported=torch.cuda.is_bf16_supported(),
                      gpu_memory_bytes=torch.cuda.get_device_properties(0).total_memory)
    path = ROOT / profile['environment_dir'] / 'environment.json'
    try:
        validate_environment(report, profile)
        for line in (ROOT / 'requirements-cloud.txt').read_text(encoding='utf-8').splitlines():
            if '==' in line and not line.lstrip().startswith('#'):
                package, expected = line.strip().split('==', 1)
                actual = importlib.metadata.version(package)
                if actual != expected:
                    raise ValueError('Required package differs: ' + package + ' ' + actual + ' != ' + expected)
        # A tiny real CUDA operation checks the installed driver, rather than trusting labels.
        tensor = torch.ones((16, 16), device='cuda', dtype=torch.bfloat16)
        report['bf16_cuda_operation_passed'] = (tensor @ tensor).sum().item() == 4096
        del tensor
        if not report['bf16_cuda_operation_passed']:
            raise ValueError('BF16 CUDA operation failed')
        torch.cuda.empty_cache()
        report['passed'] = True
    except Exception as error:
        report.update(passed=False, error_type=type(error).__name__, detail=str(error))
        shared.save(path, report)
        raise
    shared.save(path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def make_plan(keys=None):
    profile = load_profile()
    keys = profile['models'] if keys is None else keys
    if not keys or len(keys) != len(set(keys)) or set(keys) - set(profile['models']):
        raise ValueError('This profile supports distinct llava7b/gemma3_12b selections only')
    base = shared.load(ROOT / profile['base_plan'])
    items = []
    directory = ROOT / profile['config_dir']
    for key in keys:
        original = next(m for m in base['models'] if m['key'] == key)
        item = dict(original)
        for stage in ('gate', 'formal'):
            config = shared.load(ROOT / original[stage])
            for path, expected in config['expected_code_sha256'].items():
                if shared.sha(ROOT / path) != expected:
                    raise ValueError('Frozen inference code differs: ' + path)
            config.update(run_id=config['run_id'] + profile['run_suffix'],
                          output_dir=profile['output_dir'], execution_site=profile['profile'],
                          environment_profile_sha256=shared.sha(ROOT / PROFILE))
            path = directory / (config['run_id'] + '.json')
            if path.exists() and shared.load(path) != config:
                raise ValueError('Existing RTX3090 config differs; use a new version')
            shared.save(path, config)
            item[stage] = path.relative_to(ROOT).as_posix()
        items.append(item)
    base.update(models=items, total_formal_samples=len(keys) * base['sample_count_per_model'],
                execution_site=profile['profile'], environment_profile_sha256=shared.sha(ROOT / PROFILE),
                local_qwen_run_not_transferred=True)
    path = directory / ('queue-' + '-'.join(keys) + '.json')
    if path.exists() and shared.load(path) != base:
        raise ValueError('Existing RTX3090 queue differs; use a new version')
    shared.save(path, base)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'download', 'plan', 'run', 'check'))
    parser.add_argument('--model', action='append', choices=('llava7b', 'gemma3_12b'))
    parser.add_argument('--include-gated', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    profile = load_profile()
    keys = args.model or profile['models']
    env = os.environ.copy()
    env.update(PYTHONPATH=str(ROOT / 'src'), HF_HOME=str(ROOT / '.cache/huggingface'),
               PYTHONUTF8='1', TOKENIZERS_PARALLELISM='false',
               OMP_NUM_THREADS='8', MKL_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8', NUMEXPR_NUM_THREADS='8')
    if args.action in ('check', 'download', 'run'):
        environment_check()
    if args.action == 'check':
        return
    if args.action in ('prepare', 'download'):
        command = [sys.executable, 'scripts/cloud_runtime.py', args.action]
        for key in keys:
            command += ['--model', key]
        if args.include_gated:
            command += ['--include-gated']
        subprocess.run(command, env=env, check=True)
        return
    path = make_plan(keys)
    print('RTX3090 plan: ' + path.relative_to(ROOT).as_posix())
    if args.action == 'run':
        # Never launch a model in the local active queue's checkout.
        if (ROOT / 'outputs/formal_v3_18turn_runs/serial_queue.lock').exists():
            raise SystemExit('Another serial controller holds this checkout lock; inspect it before restarting.')
        manifest = shared.load(ROOT / shared.MANIFEST)
        if shared.sha(ROOT / manifest['dataset_path']) != manifest['dataset_sha256']:
            raise ValueError('Frozen dataset fingerprint mismatch')
        for image in manifest['images']:
            if shared.sha(shared.safe_path(ROOT, image['path'])) != image['sha256']:
                raise ValueError('Image fingerprint mismatch: ' + image['path'])
        # Gate results made in a different torch/Python environment must not be reused as a smoke pass.
        for key in keys:
            deployment = ROOT / 'outputs/model_deployment' / (key + '.json')
            if deployment.exists():
                report = shared.load(deployment)
                runtime = report.get('smoke_check', {}).get('runtime', {})
                if str(runtime.get('torch', '')).split('+')[0] != profile['torch_version']:
                    report.pop('smoke_check', None)
                    shared.save(deployment, report)
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        subprocess.run([sys.executable, 'scripts/run_formal_v3_18turn_queue.py', '--plan',
                        path.relative_to(ROOT).as_posix()], env=env, check=True)
        print('Requested RTX3090 model queue finished: ' + ', '.join(keys))


if __name__ == '__main__':
    main()
