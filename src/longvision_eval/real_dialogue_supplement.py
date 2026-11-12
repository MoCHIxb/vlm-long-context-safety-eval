"""Frozen-user/actual-assistant supplement; no model judging or interventions.

Uses the existing generated-history checkpoint executor, without modifying its
formal-v3 model path. New data is shipped as hashed gzip JSONL, independent of
the large original materialization on the execution machine.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import platform
import re
import sys
from importlib.metadata import version, PackageNotFoundError
import os

from .dataset import load_json
from .free_history_supplement import digest, save_artifact, verify_artifact
from .provenance import file_sha256
from .runner import write_json_atomic

VERSION = 'real-dialogue-v1-qwen3'
SOURCE_SHA = 'ffd78bcce1a0548905dd8730d6d0dd17ee4191649e4befc42cbec981d75b571f'
CONDITIONS = ('C00', 'C09', 'C10', 'C11')
IMPLEMENTATION = (
    'src/longvision_eval/real_dialogue_supplement.py',
    'src/longvision_eval/free_history_supplement.py',
    'scripts/run_real_dialogue_supplement.py',
)


def write_gzip_jsonl(path, records):
    """Same-environment deterministic bundle: no timestamps or source filename."""
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as stream:
            for record in records:
                stream.write((json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n').encode('utf-8'))


def read_bundle(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def selected(record):
    return (record['track'] == 'harmful_controlled' and record['condition_id'] in CONDITIONS) or (
        record['track'] == 'benign_controlled' and record['condition_id'] == 'B08')


def derive_records(source):
    """Preserve each original user message exactly; append only existing goals.

    Gold, reference assistant and construction annotations never enter the run
    records. Design annotations are retained separately, explicitly not truth.
    """
    source = [r for r in source if selected(r)]
    pairs = {}
    for r in source:
        if r['track'] == 'harmful_controlled':
            pairs.setdefault(r['pair_id'], {})[r['label']] = r
    records, annotations = [], []
    for r in sorted(source, key=lambda r: r['sample_id']):
        if len(r['turns']) != 18 or [t['turn_index'] for t in r['turns']] != list(range(1, 19)):
            raise ValueError('Expected original contiguous 18-turn records')
        turns = [dict(turn_index=t['turn_index'], user=deepcopy(t['user'])) for t in r['turns']]
        if r['track'] == 'harmful_controlled':
            pair = pairs[r['pair_id']]
            if set(pair) != {'safe', 'unsafe'}:
                raise ValueError('Incomplete source goal pair')
            # Pair provenance must match; never link a goal from another scene.
            for other in pair.values():
                if any(other[k] != r[k] for k in ('seed_id', 'split', 'condition_id')):
                    raise ValueError('Source pair crosses scenario/split/condition')
            for label in ('safe', 'unsafe'):
                for a, b in zip(pair[label]['turns'][:17], r['turns'][:17]):
                    if a['user'] != b['user']:
                        raise ValueError('Source goal pair does not share its first 17 user turns')
            followups = [pair[r['label']], pair['safe']]
            roles = ['repeat_original_goal', 'paired_benign_recovery'] if r['label'] == 'unsafe' else [
                'repeat_original_benign_goal', 'repeat_original_benign_goal']
        else:
            followups, roles = [r, r], ['repeat_original_benign_goal']*2
        origins = []
        for index, (origin, role) in enumerate(zip(followups, roles), 19):
            user = deepcopy(origin['turns'][-1]['user'])
            turns.append(dict(turn_index=index, user=user))
            origins.append(dict(turn_index=index, source_sample_id=origin['sample_id'], source_turn_index=18, role=role))
        keys = ('seed_id', 'split', 'pair_id', 'schedule_pair_id', 'condition_id', 'track', 'label',
                'risk_category', 'risk_subcategory', 'benign_subcategory', 'language', 'source')
        record = {k: deepcopy(r.get(k)) for k in keys}
        record.update(schema_version=VERSION, sample_id='RD1-'+r['sample_id'],
            source_sample_id=r['sample_id'], source_record_sha256=digest(r),
            variables=dict(r['variables'], turn_count=20, original_turn_count=18),
            turns=turns, followup_origins=origins,
            cohort_note='label identifies original turn-18 goal, not all requests in the full session')
        records.append(record)
        annotations.append(dict(sample_id=record['sample_id'], source_sample_id=r['sample_id'],
            status='design_annotations_not_independent_truth',
            original_gold=[dict(turn_index=t['turn_index'], design_gold=t.get('gold')) for t in r['turns']],
            followup_origins=origins,
            evidence_onset_turn=None, evidence_onset_status='requires_prefix_review',
            response_history='not_yet_generated'))
    if len({r['sample_id'] for r in records}) != len(records):
        raise ValueError('Duplicate sample IDs')
    return records, annotations


def choose_gate(records):
    """Four real calibration trajectories; their committed turns are not rerun."""
    cal = [r for r in records if r['split'] == 'calibration']
    choices = [
        ('harmful_controlled', 'unsafe', 'static_initial_bundle'),
        ('harmful_controlled', 'safe', 'dynamic_incremental'),
        ('benign_controlled', 'safe', 'static_initial_bundle'),
        ('benign_controlled', 'safe', 'dynamic_incremental')]
    gate = []
    for track, label, schedule in choices:
        candidates = [r for r in cal if r['track'] == track and r['label'] == label and
            r['variables']['visual_evidence_schedule'] == schedule and
            (track != 'harmful_controlled' or r['condition_id'] == 'C00')]
        if not candidates:
            raise ValueError('Required calibration gate stratum is missing')
        gate.append(max(candidates, key=lambda r: (sum(len(t['user']['content']) for t in r['turns']), r['sample_id'])))
    if len({r['sample_id'] for r in gate}) != 4:
        raise ValueError('Gate must contain four distinct calibration trajectories')
    return gate


def dataset_summary(records):
    return dict(trajectories=len(records), model_calls=sum(len(r['turns']) for r in records),
        seeds=len({r['seed_id'] for r in records}), split_counts=dict(Counter(r['split'] for r in records)),
        track_counts=dict(Counter(r['track'] for r in records)),
        condition_counts=dict(Counter(r['condition_id'] for r in records)),
        visible_image_count=len({p for r in records for t in r['turns'] for p in t['user']['images']}))


def build_release(root):
    source_path = root / 'data/processed/formal_v3_18turn.jsonl'
    if file_sha256(source_path) != SOURCE_SHA:
        raise ValueError('Frozen source dataset changed')
    # Stream selection avoids retaining all 240 MB of original JSON objects.
    source = []
    with source_path.open(encoding='utf-8') as stream:
        for line in stream:
            r = json.loads(line)
            if selected(r):
                source.append(r)
    records, annotations = derive_records(source)
    expected = dict(trajectories=1408, model_calls=28160, seeds=144,
                    split_counts={'calibration':144, 'primary':976, 'heldout':288})
    summary = dataset_summary(records)
    for k, v in expected.items():
        if summary[k] != v:
            raise ValueError('Unexpected panel: '+k)
    assets = {x['path']: x for x in load_json(root/'configs/cloud/runtime_manifest.json')['images']}
    used = sorted({p for r in records for t in r['turns'] for p in t['user']['images']})
    image_hashes = {}
    for name in used:
        path = (root/name).resolve()
        path.relative_to((root/'data/raw/images').resolve())
        if name not in assets or file_sha256(path) != assets[name]['sha256']:
            raise ValueError('Missing/changed frozen image: '+name)
        image_hashes[name] = assets[name]['sha256']
    release = root/'data/releases/real_dialogue_v1'
    release.mkdir(parents=True, exist_ok=True)
    run_path, annotation_path = release/'panel.jsonl.gz', release/'design_annotations.jsonl.gz'
    write_gzip_jsonl(run_path, records)
    write_gzip_jsonl(annotation_path, annotations)
    manifest = dict(version=VERSION, source_dataset_sha256=SOURCE_SHA,
        panel_path=run_path.relative_to(root).as_posix(), panel_sha256=file_sha256(run_path),
        design_annotations_path=annotation_path.relative_to(root).as_posix(),
        design_annotations_sha256=file_sha256(annotation_path),
        summary=summary, gate_ids=[r['sample_id'] for r in choose_gate(records)],
        image_sha256=image_hashes,
        user_script_transform='Original 18 user turns unchanged; two existing-goal repeats/recovery appended.',
        semantic_status='Controlled source scripts preserved, not reviewed natural/adaptive conversations.',
        annotations_status='Design labels only; not independent per-turn safety judgments.')
    write_json_atomic(release/'manifest.json', manifest)
    return manifest


def prepare(root, config_path, site):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', site):
        raise ValueError('Use a short alphanumeric/dash/underscore site ID')
    config = load_json(config_path)
    if config['model_key'] != 'qwen3vl8b':
        raise ValueError('This release runs only Qwen3-VL-8B')
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
        raise ValueError('Frozen Qwen3 model configuration changed')
    model = load_json(model_path)
    if model['key'] != config['model_key'] or model['model_class'] != 'Qwen3VLForConditionalGeneration':
        raise ValueError('Unexpected model identity')
    identity = dict(protocol=config, model_configuration=model, release_manifest_sha256=file_sha256(manifest_path),
        implementation_sha256=code, packages=packages, python=sys.version, system=platform.system(), site=site,
        execution_env={k:os.environ.get(k) for k in ('HF_HOME','PYTORCH_ALLOC_CONF','PYTORCH_CUDA_ALLOC_CONF',
            'CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','MKL_NUM_THREADS')})
    fingerprint = digest(identity)
    output = root/'outputs/real_dialogue_supplement'/f'rd-v1-qwen3vl8b-{site}-{fingerprint[:12]}'
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
    value = dict(version=VERSION, sample_id=record['sample_id'], source_sample_id=record['source_sample_id'],
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
