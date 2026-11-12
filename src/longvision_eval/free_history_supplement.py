"""Separate generated-history supplement with per-turn validated checkpoints."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import platform
import re
import sys

from .dataset import load_json
from .runner import user_message, write_json_atomic
from .provenance import file_sha256


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def save_artifact(path, payload):
    payload = dict(payload)
    payload.pop('_content_sha256', None)
    payload['_content_sha256'] = digest(payload)
    write_json_atomic(path, payload)


def history_digest(messages, root):
    portable = []
    for message in messages:
        if isinstance(message['content'], str):
            portable.append(message)
        else:
            content = []
            for item in message['content']:
                item = dict(item)
                if item['type'] == 'image':
                    item['path'] = Path(item['path']).resolve().relative_to(root.resolve()).as_posix()
                content.append(item)
            portable.append({'role': message['role'], 'content': content})
    return digest(portable)


def verify_artifact(payload, record, fingerprint, root, complete=False):
    value = dict(payload)
    checksum = value.pop('_content_sha256', None)
    if checksum != digest(value):
        raise ValueError('Checkpoint/result checksum differs; preserve it for investigation')
    if value.get('fingerprint') != fingerprint or value.get('record_sha256') != digest(record):
        raise ValueError('Checkpoint/result source or run differs')
    turns = value.get('turns', [])
    if len(turns) > len(record['turns']) or (complete and len(turns) != len(record['turns'])):
        raise ValueError('Invalid checkpoint/result turn count')
    messages = []
    for source, turn in zip(record['turns'], turns):
        if turn.get('history_before_user_sha256') != history_digest(messages, root):
            raise ValueError('Saved generated prefix differs')
        messages.append(user_message(source, root))
        response = turn['response']
        if turn['turn_index'] != source['turn_index'] or response.get('source') != 'model':
            raise ValueError('History must contain actual model responses at matching turns')
        if not isinstance(response.get('text'), str) or not response['text'].strip():
            raise ValueError('Saved response is empty')
        if turn.get('input_history_sha256') != history_digest(messages, root):
            raise ValueError('Saved input history differs')
        messages.append({'role': 'assistant', 'content': response['text']})
    return messages


def run_trajectory(record, adapter, generation, root, directory, fingerprint, on_turn=None):
    """Resume from the last complete response; never insert assistant_context."""
    sid = record['sample_id']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', sid):
        raise ValueError('Unsafe sample filename')
    final = directory / (sid + '.json')
    checkpoint = directory / 'checkpoints' / (sid + '.json')
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        saved = load_json(final)
        verify_artifact(saved, record, fingerprint, root, complete=True)
        return saved
    if checkpoint.exists():
        saved = load_json(checkpoint)
        messages = verify_artifact(saved, record, fingerprint, root)
    else:
        saved = {k: record.get(k) for k in ['sample_id', 'seed_id', 'split', 'pair_id', 'schedule_pair_id',
                 'condition_id', 'track', 'label', 'risk_category', 'variables']}
        saved.update(fingerprint=fingerprint, record_sha256=digest(record), history_mode='model_generated_every_turn', turns=[])
        messages = []
    for index in range(len(saved['turns']), len(record['turns'])):
        source = record['turns'][index]
        prefix_sha = history_digest(messages, root)
        messages.append(user_message(source, root))
        input_sha = history_digest(messages, root)
        response = adapter.generate(messages, dict(generation)).to_dict()
        if not isinstance(response.get('text'), str) or not response['text'].strip():
            raise ValueError('Empty model response; current turn was not committed')
        response['source'] = 'model'
        saved['turns'].append({'turn_index': source['turn_index'], 'image_count': len(source['user']['images']),
                               'history_before_user_sha256': prefix_sha,
                               'input_history_sha256': input_sha, 'response': response})
        messages.append({'role': 'assistant', 'content': response['text']})
        save_artifact(checkpoint, saved)
        if on_turn:
            on_turn(index + 1, len(record['turns']), response)
    saved['complete'] = True
    save_artifact(final, saved)
    return load_json(final)


def prepare(root, protocol_path, model_key, site):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', site):
        raise ValueError('Use a short site identifier with letters, digits, underscore or dash')
    protocol = load_json(protocol_path)
    if model_key not in protocol['models']:
        raise ValueError('Unknown model')
    data = root / protocol['dataset_path']
    if file_sha256(data) != protocol['dataset_sha256']:
        raise ValueError('Frozen source dataset changed')
    records = []
    with data.open(encoding='utf-8') as stream:
        for line in stream:
            record = json.loads(line)
            if record['condition_id'] in protocol['conditions']:
                records.append(record)
    order = dict(zip(protocol['conditions'], protocol['turn_counts']))
    records.sort(key=lambda r: (r['seed_id'], order[r['condition_id']], r['variables']['visual_evidence_schedule'], r['label']))
    if len(records) != protocol['expected_trajectories'] or len({r['seed_id'] for r in records}) != protocol['expected_seed_count']:
        raise ValueError('Unexpected supplement panel size')
    if any(len(r['turns']) != order[r['condition_id']] for r in records):
        raise ValueError('Condition/turn count mismatch')
    if sum(len(r['turns']) for r in records) != protocol['expected_model_calls']:
        raise ValueError('Unexpected generation-call count')
    assets = {i['path']: i['sha256'] for i in load_json(root / protocol['asset_manifest'])['images']}
    used = sorted({p for r in records for t in r['turns'] for p in t['user']['images']})
    for name in used:
        path = (root / name).resolve()
        path.relative_to((root / 'data/raw/images').resolve())
        if name not in assets or file_sha256(path) != assets[name]:
            raise ValueError('Frozen image changed: ' + name)
    # Preserve the existing formal implementation; pin both its files and the new wrapper.
    reference = load_json(root / 'configs/runs/formal_v3_18turn/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024.json')
    code = {}
    for name, expected in reference['expected_code_sha256'].items():
        code[name] = file_sha256(root / name)
        if code[name] != expected:
            raise ValueError('Frozen model execution implementation changed: ' + name)
    for name in ['src/longvision_eval/free_history_supplement.py', 'scripts/run_free_history_supplement.py']:
        code[name] = file_sha256(root / name)
    packages = {}
    for name in ['torch', 'transformers', 'bitsandbytes', 'accelerate', 'pillow']:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    model = load_json(root / protocol['models'][model_key])
    identity = {'protocol': protocol, 'model_key': model_key, 'model_configuration': model, 'site': site,
                'implementation_sha256': code, 'packages': packages, 'python': sys.version,
                'system': platform.system(), 'image_sha256': {n: assets[n] for n in used},
                'execution_env': {k: os.environ.get(k) for k in ['PYTORCH_ALLOC_CONF', 'PYTORCH_CUDA_ALLOC_CONF',
                    'CUDA_VISIBLE_DEVICES', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']}}
    fingerprint = digest(identity)
    directory = root / 'outputs/free_history_supplement' / f'fh-v1-{model_key}-{site}-{fingerprint[:12]}'
    directory.mkdir(parents=True, exist_ok=True)
    manifest = dict(identity, fingerprint=fingerprint, sample_ids=[r['sample_id'] for r in records])
    path = directory / 'manifest.json'
    if path.exists() and load_json(path) != manifest:
        raise ValueError('Existing supplement manifest differs')
    write_json_atomic(path, manifest)
    first_seed = next(r['seed_id'] for r in records if r['split'] == 'calibration')
    gate = []
    for condition, schedule, label in [('C01', 'static_initial_bundle', 'safe'), ('C01', 'dynamic_incremental', 'unsafe'),
                                      ('C13', 'static_initial_bundle', 'unsafe'), ('C13', 'dynamic_incremental', 'safe')]:
        gate.append(next(r for r in records if r['seed_id'] == first_seed and r['condition_id'] == condition and
                         r['variables']['visual_evidence_schedule'] == schedule and r['label'] == label))
    write_json_atomic(directory / 'panel.json', {'formal_ids': manifest['sample_ids'], 'gate_ids': [r['sample_id'] for r in gate],
                      'formal_trajectories': len(records), 'formal_model_calls': sum(len(r['turns']) for r in records),
                      'gate_model_calls': sum(len(r['turns']) for r in gate),
                      'split_counts': dict(Counter(r['split'] for r in records)), 'planning_only_artifact': True})
    return protocol, model, records, gate, directory, fingerprint


class RunLock:
    """OS-released local lock, including after power loss; a leftover file is harmless."""
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open('a+b')
        if self.path.stat().st_size == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.stream.close()
            raise RuntimeError('Another generated-history model run holds this checkout GPU lock')
        return self

    def __exit__(self, *exc):
        if os.name == 'nt':
            import msvcrt
            self.stream.seek(0)
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        self.stream.close()


def summarize(directory, records, fingerprint, root):
    calls = history_truncated = final_truncated = complete = 0
    max_input = max_peak = seconds = 0
    errors = []
    goal_pairs = {}
    for record in records:
        result = directory / (record['sample_id'] + '.json')
        checkpoint = directory / 'checkpoints' / (record['sample_id'] + '.json')
        if result.exists() or checkpoint.exists():
            payload = load_json(result if result.exists() else checkpoint)
            verify_artifact(payload, record, fingerprint, root, complete=result.exists())
            complete += result.exists()
            if result.exists():
                key = (record.get('seed_id'), record.get('condition_id'),
                       record.get('variables', {}).get('visual_evidence_schedule'))
                goal_pairs.setdefault(key, {})[record.get('label')] = payload['turns'][-1]['history_before_user_sha256']
            for index, turn in enumerate(payload['turns']):
                response = turn['response']
                calls += 1
                is_final = index == len(record['turns']) - 1
                history_truncated += bool(response.get('truncated')) and not is_final
                final_truncated += bool(response.get('truncated')) and is_final
                max_input = max(max_input, response.get('input_tokens') or 0)
                max_peak = max(max_peak, response.get('peak_gpu_memory_mb') or 0)
                seconds += response.get('duration_seconds') or 0
        error = directory / 'errors' / (record['sample_id'] + '.json')
        if error.exists():
            errors.append(record['sample_id'])
    summary = {'planned': len(records), 'completed': complete, 'pending': len(records) - complete,
               'committed_model_calls': calls, 'error_count': len(errors), 'failed_sample_ids': errors,
               'truncated_history_calls': history_truncated, 'truncated_final_calls': final_truncated,
               'max_input_tokens': max_input, 'max_peak_gpu_memory_mib': max_peak,
               'total_generation_seconds': round(seconds, 4), 'human_review_completed': False,
               'complete': complete == len(records) and not errors}
    paired = [p for p in goal_pairs.values() if 'safe' in p and 'unsafe' in p]
    summary.update(goal_pairs_completed=len(paired),
                   goal_pairs_with_identical_generated_prefix=sum(p['safe'] == p['unsafe'] for p in paired))
    write_json_atomic(directory / 'technical_summary.json', summary)
    return summary
