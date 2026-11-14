"""Additional model entry points; leaves the deployed Qwen3 v1 fingerprints intact.

The pinned data bundle is shared with Qwen3. Version names of the source bundle
are provenance, not the identity of the model generating these responses.
"""
from __future__ import annotations
from copy import deepcopy
from importlib.metadata import version, PackageNotFoundError
import os
import platform
import re
import sys

from .dataset import load_json
from .provenance import file_sha256
from .runner import write_json_atomic
from .free_history_supplement import digest, save_artifact, verify_artifact
from .real_dialogue_supplement import read_bundle, dataset_summary

VERSION = 'real-dialogue-v1-multimodel'
MODEL_CLASSES = {'llava7b': 'LlavaOnevisionForConditionalGeneration',
                 'gemma3_12b': 'Gemma3ForConditionalGeneration'}
IMPLEMENTATION = ('src/longvision_eval/real_dialogue_models.py',
                  'src/longvision_eval/real_dialogue_supplement.py',
                  'src/longvision_eval/free_history_supplement.py',
                  'scripts/run_real_dialogue_models.py')


def prepare(root, config_path, site):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', site):
        raise ValueError('Use a short alphanumeric/dash/underscore site ID')
    config = load_json(config_path)
    if config['model_key'] not in MODEL_CLASSES:
        raise ValueError('Select llava7b or gemma3_12b')
    manifest_path = root/config['release_manifest']
    if file_sha256(manifest_path) != config['release_manifest_sha256']:
        raise ValueError('Release manifest checksum mismatch')
    release = load_json(manifest_path)
    panel_path = root/release['panel_path']
    if file_sha256(panel_path) != release['panel_sha256']:
        raise ValueError('Panel checksum mismatch')
    records = read_bundle(panel_path)
    if dataset_summary(records) != release['summary']:
        raise ValueError('Panel summary differs from frozen release')
    if len({r['sample_id'] for r in records}) != len(records):
        raise ValueError('Duplicate run sample IDs')
    for record in records:
        if [t['turn_index'] for t in record['turns']] != list(range(1,21)):
            raise ValueError('Invalid turn sequence')
        for t in record['turns']:
            if set(t) != {'turn_index', 'user'} or set(t['user']) != {'content','images'}:
                raise ValueError('Reference answers or oracle turn fields are forbidden')
    used = {p for r in records for t in r['turns'] for p in t['user']['images']}
    if used != set(release['image_sha256']):
        raise ValueError('Image set differs')
    for name, expected in release['image_sha256'].items():
        path = (root/name).resolve()
        path.relative_to((root/'data/raw/images').resolve())
        if file_sha256(path) != expected:
            raise ValueError('Image checksum mismatch: '+name)
    code = {}
    for name, expected in config['frozen_executor_sha256'].items():
        actual = file_sha256(root/name)
        if actual != expected:
            raise ValueError('Frozen executor changed: '+name)
        code[name] = actual
    for name in IMPLEMENTATION:
        code[name] = file_sha256(root/name)
    packages = {}
    for name in ('torch','transformers','bitsandbytes','accelerate','pillow'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    model_path = root/config['model_config']
    if file_sha256(model_path) != config['model_config_sha256']:
        raise ValueError('Frozen model configuration changed')
    model = load_json(model_path)
    if model['key'] != config['model_key'] or model['model_class'] != MODEL_CLASSES[config['model_key']]:
        raise ValueError('Unexpected model identity')
    identity = dict(protocol=config, model_configuration=model, release_manifest_sha256=file_sha256(manifest_path),
        implementation_sha256=code, packages=packages, python=sys.version, system=platform.system(), site=site,
        execution_env={k:os.environ.get(k) for k in ('HF_HOME','PYTORCH_ALLOC_CONF','PYTORCH_CUDA_ALLOC_CONF',
            'CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','MKL_NUM_THREADS')})
    fingerprint = digest(identity)
    output = root/'outputs/real_dialogue_supplement'/f'rd-v1-{config["model_key"]}-{site}-{fingerprint[:12]}'
    output.mkdir(parents=True, exist_ok=True)
    path = output/'manifest.json'
    run_manifest = dict(identity, fingerprint=fingerprint, sample_ids=[r['sample_id'] for r in records],
        gate_ids=release['gate_ids'], summary=release['summary'])
    if path.exists() and load_json(path) != run_manifest:
        raise ValueError('Existing run manifest differs')
    write_json_atomic(path, run_manifest)
    gate = [next(r for r in records if r['sample_id']==sid) for sid in release['gate_ids']]
    return config, model, records, gate, output, fingerprint


def export_trajectory(root, record, payload, output, fingerprint):
    """Self-contained actual transcript plus blank independent-label worksheet."""
    verify_artifact(payload, record, fingerprint, root, complete=True)
    rows = []
    for source, generated in zip(record['turns'], payload['turns']):
        rows.append(dict(turn_index=source['turn_index'], user=deepcopy(source['user']),
            response=deepcopy(generated['response']),
            history_before_user_sha256=generated['history_before_user_sha256'],
            input_history_sha256=generated['input_history_sha256']))
    model_key = load_json(output/'manifest.json')['protocol']['model_key']
    value = dict(version=VERSION, model_key=model_key, source_release_version='real-dialogue-v1-qwen3', sample_id=record['sample_id'], source_sample_id=record['source_sample_id'],
        seed_id=record['seed_id'], split=record['split'], track=record['track'], label=record['label'],
        condition_id=record['condition_id'], variables=record['variables'], fingerprint=fingerprint,
        source_record_sha256=digest(record), history_mode='actual_model_outputs', complete=True,
        original_endpoint_turn=18, followup_origins=record['followup_origins'], turns=rows,
        assessment_performed=False)
    directory = output/'trajectories'
    directory.mkdir(exist_ok=True)
    path = directory/(record['sample_id']+'.json')
    expected = dict(value, _content_sha256=digest(value))
    if path.exists() and load_json(path) != expected:
        raise ValueError('Existing exported transcript changed; preserve it for audit')
    if not path.exists():
        save_artifact(path,value)
    directory = output/'assessment_to_fill'
    directory.mkdir(exist_ok=True)
    path = directory/(record['sample_id']+'.json')
    # Never overwrite an annotator's work on resume.
    if not path.exists():
        fields = ('request_harmful','joint_intent_harmful','harmful_output','refusal',
                  'appropriate_refusal','safe_redirection','task_completion','safety_awareness',
                  'cumulative_harmful_assistance','evidence_refs','unknown_reason')
        write_json_atomic(path, dict(sample_id=record['sample_id'], fingerprint=fingerprint,
            trajectory_sha256=digest(value), status='unreviewed', evidence_onset_turn=None,
            turns=[dict(turn_index=t['turn_index'], **{k:None for k in fields}) for t in rows]))
    return value
