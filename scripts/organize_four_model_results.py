"""Validate and index four fixed-reference model panels without moving source results."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from longvision_eval.dataset import select_records


def diskpath(path):
    value = os.path.abspath(path)
    return Path('\\\\?\\' + value) if os.name == 'nt' and not value.startswith('\\\\?\\') else Path(value)


def read(path):
    return json.loads(diskpath(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(diskpath(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def dump(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def jsonl(path, rows):
    with path.open('wb') as f:
        for row in rows:
            f.write((json.dumps(row, ensure_ascii=False) + '\n').encode('utf-8'))


def register(index, row):
    sid = row['sample_id']
    if sid in index:
        if index[sid]['source_sha256'] != row['source_sha256']:
            raise ValueError('Conflicting duplicate success for ' + sid)
        return False
    index[sid] = row
    return True


def reference_echo(result):
    past = result['turns'][:-1]
    return bool(past) and all(t['response'].get('source') == 'fixed_reference' for t in past) and (
        result['turns'][-1]['response']['text'].strip().casefold() == past[-1]['response']['text'].strip().casefold())


def main():
    asset = read(ROOT / 'configs/cloud/runtime_manifest.json')
    dataset = ROOT / asset['dataset_path']
    dataset_sha = sha(dataset)
    if dataset_sha != asset['dataset_sha256']:
        raise ValueError('Dataset differs')
    canonical = {}
    with dataset.open(encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            row = {k: r[k] for k in ['sample_id', 'seed_id', 'split', 'track', 'label', 'condition_id', 'risk_category', 'variables']}
            row['turns'] = [{'turn_index': t['turn_index'], 'image_count': len(t['user']['images']),
                             'risk_state': t['gold']['risk_state'], 'expected_behavior': t['gold']['expected_behavior'],
                             'reference': t.get('assistant_context')} for t in r['turns']]
            if r['sample_id'] in canonical:
                raise ValueError('Duplicate canonical sample')
            canonical[r['sample_id']] = row
    if len(canonical) != 4864:
        raise ValueError('Wrong canonical panel')
    qwen3 = ROOT / 'outputs/cloud_imports/qwen3-b597bd0/outputs'
    cloud = ROOT / 'outputs/cloud_imports/llava-gemma-20261112T044919Z/outputs'
    groups = {
        'qwen25vl7b': [(ROOT / 'outputs/formal_v3_18turn_runs/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024',
            ROOT / 'configs/runs/formal_v3_18turn/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024.json')],
        'qwen3vl8b': [], 'llava7b': [], 'gemma3_12b': []}
    for key, parent, config_dir in [
            ('qwen3vl8b', qwen3 / 'cloud_rtx3090_qwen3_runs', qwen3 / 'cloud_rtx3090_qwen3_configs'),
            ('llava7b', cloud / 'cloud_rtx3090_runs', cloud / 'cloud_rtx3090_configs'),
            ('gemma3_12b', cloud / 'cloud_rtx3090_runs', cloud / 'cloud_rtx3090_configs')]:
        configs = {c['run_id']: p for p in config_dir.glob('*.json') if 'run_id' in (c := read(p))}
        for path in sorted(parent.glob('formal-v318-' + key + '-*')):
            if path.name not in configs:
                raise ValueError('No source config for ' + path.name)
            groups[key].append((path, configs[path.name]))
        if not groups[key]:
            raise ValueError('Missing model group ' + key)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'outputs/unified_formal_v3_18turn' / stamp
    out.mkdir(parents=True)
    (out / 'models').mkdir()
    (out / 'records').mkdir()
    (out / 'errors').mkdir()
    all_rows, all_errors, summaries, source_runs = {}, [], [], []
    file_hashes = {}
    expected_generation = {'max_new_tokens': 1024, 'do_sample': False, 'repetition_penalty': 1.05}
    for key, sources in groups.items():
        index = {}
        model_errors, runtime_groups = [], Counter()
        first_config, first_model = None, None
        duplicates = 0
        for directory, config_path in sources:
            config, manifest = read(config_path), read(directory / 'run_manifest.json')
            normalized = {k: v for k, v in config.items() if k not in ['run_id', 'sample_ids', 'recovery_note', 'output_dir']}
            if first_config is None:
                first_config, first_model = normalized, manifest['model_configuration']
            if normalized != first_config or manifest['model_configuration'] != first_model:
                raise ValueError('Run variants changed experimental settings for ' + key)
            selected = select_records(canonical.values(), sample_ids=set(config.get('sample_ids', [])) or None,
                        tracks=set(config.get('tracks', [])) or None,
                        condition_ids=set(config.get('condition_ids', [])) or None, limit=config.get('limit'))
            expected = {r['sample_id'] for r in selected}
            prov = manifest['provenance']
            if set(manifest['sample_ids']) != expected or len(manifest['sample_ids']) != len(expected):
                raise ValueError('Manifest selection differs')
            if config['generation'] != expected_generation or config['history_mode'] != 'fixed_reference':
                raise ValueError('Wrong generation/history protocol')
            if prov['dataset_sha256'] != dataset_sha or prov['experiment_stage'] != 'formal_18turn':
                raise ValueError('Wrong dataset or stage')
            if prov['configuration_sha256'] != canonical_hash({'run': config, 'model': manifest['model_configuration']}):
                raise ValueError('Source configuration hash differs')
            if prov['implementation_sha256'] != config['expected_code_sha256']:
                raise ValueError('Source implementation manifest differs')
            for name, h in config['expected_code_sha256'].items():
                if sha(ROOT / name) != h:
                    raise ValueError('Frozen source code differs')
            for p in [config_path, directory / 'run_manifest.json']:
                file_hashes[p.relative_to(ROOT).as_posix()] = sha(p)
            count = 0
            for path in sorted(directory.glob('V318-*.json')):
                data = read(path)
                sid = data['sample_id']
                if path.stem != sid or sid not in expected:
                    raise ValueError('Unexpected/renamed result ' + str(path))
                record = canonical[sid]
                for field in ['seed_id', 'split', 'track', 'label', 'condition_id', 'risk_category', 'variables']:
                    if data.get(field) != record[field]:
                        raise ValueError('Sample metadata differs: ' + sid + '/' + field)
                run = data['run']
                if run['provenance'] != prov or run['run_id'] != manifest['run_id'] or run['model_id'] != manifest['model_id']:
                    raise ValueError('Per-result provenance differs')
                if run['generation'] != expected_generation or run['history_mode'] != 'fixed_reference':
                    raise ValueError('Per-result inference settings differ')
                if run.get('system_prompt') or run.get('response_instruction'):
                    raise ValueError('Unexpected prompt override')
                if len(data['turns']) != len(record['turns']):
                    raise ValueError('Incomplete result turn history')
                for i, (turn, original) in enumerate(zip(data['turns'], record['turns'])):
                    for field in ['turn_index', 'image_count', 'risk_state', 'expected_behavior']:
                        if turn[field] != original[field]:
                            raise ValueError('Turn metadata differs')
                    if i < len(record['turns']) - 1:
                        if turn['response']['source'] != 'fixed_reference' or turn['response']['text'] != original['reference']:
                            raise ValueError('Unexpected generated/nonmatching historical context')
                final = data['turns'][-1]['response']
                if final.get('source') != 'model':
                    raise ValueError('No generated final response')
                words = re.findall(r'\w+', final['text'].lower())
                grams = [tuple(words[i:i+3]) for i in range(len(words) - 2)]
                repeated = len(words) >= 40 and len(set(grams)) / len(grams) < .15
                source_name = path.relative_to(ROOT).as_posix()
                file_hashes[source_name] = sha(path)
                metrics = {k: final.get(k) for k in ['input_tokens', 'output_tokens', 'duration_seconds', 'peak_gpu_memory_mb', 'truncated']}
                row = {k: record[k] for k in ['sample_id', 'seed_id', 'split', 'track', 'label', 'condition_id', 'risk_category']}
                row.update(model_key=key, status='model_output_available', visual_schedule=record['variables']['visual_evidence_schedule'],
                           source_path=source_name, source_sha256=file_hashes[source_name], source_run_id=manifest['run_id'],
                           source_configuration_sha256=prov['configuration_sha256'], source_runtime_sha256=canonical_hash(run['runtime']),
                           final_response_metrics=metrics, empty_final_answer=not final['text'].strip(),
                           highly_repetitive_final_answer_heuristic=repeated,
                           reference_acknowledgment_echo=reference_echo(data), safety_label=None)
                fresh = register(index, row)
                duplicates += not fresh
                if fresh:
                    runtime_groups[row['source_runtime_sha256']] += 1
                count += 1
            for path in sorted((directory / 'errors').glob('*.json')):
                error = read(path)
                if error['sample_id'] not in expected or path.stem != error['sample_id']:
                    raise ValueError('Error points outside source selection')
                name = path.relative_to(ROOT).as_posix()
                file_hashes[name] = sha(path)
                model_errors.append({'model_key': key, 'sample_id': error['sample_id'], 'source_path': name,
                    'source_sha256': file_hashes[name], 'source_run_id': manifest['run_id'],
                    'error_record': error, 'classification': 'technical_failure', 'random_missingness_established': False,
                    'safety_label': None})
            source_runs.append({'model_key': key, 'run_id': manifest['run_id'], 'source_directory': directory.relative_to(ROOT).as_posix(),
                                'config_path': config_path.relative_to(ROOT).as_posix(), 'expected_in_this_run': len(expected),
                                'successful_files': count, 'error_files': len(list((directory / 'errors').glob('*.json')))})
        failed_ids = {r['sample_id'] for r in model_errors} - index.keys()
        missing = set(canonical) - index.keys() - failed_ids
        for sid in sorted(set(canonical) - index.keys()):
            record = canonical[sid]
            row = {k: record[k] for k in ['sample_id', 'seed_id', 'split', 'track', 'label', 'condition_id', 'risk_category']}
            row.update(model_key=key, status='technical_failure' if sid in failed_ids else 'missing_unexplained',
                       visual_schedule=record['variables']['visual_evidence_schedule'], source_path=None, source_sha256=None,
                       final_response_metrics=None, safety_label=None,
                       error_source_paths=[e['source_path'] for e in model_errors if e['sample_id'] == sid])
            index[sid] = row
        success = [r for r in index.values() if r['status'] == 'model_output_available']
        summary = {'model_key': key, 'planned': len(canonical), 'successful_outputs': len(success),
            'unique_technical_failure_samples': len(failed_ids), 'preserved_error_records': len(model_errors),
            'missing_unexplained': len(missing), 'duplicate_successes': duplicates,
            'truncated_final_answers': sum(bool(r['final_response_metrics']['truncated']) for r in success),
            'empty_final_answers': sum(r['empty_final_answer'] for r in success),
            'highly_repetitive_final_answer_heuristic': sum(r['highly_repetitive_final_answer_heuristic'] for r in success),
            'reference_acknowledgment_echo': sum(r['reference_acknowledgment_echo'] for r in success),
            'max_input_tokens': max((r['final_response_metrics']['input_tokens'] or 0 for r in success), default=0),
            'max_peak_torch_allocated_mib': max((r['final_response_metrics']['peak_gpu_memory_mb'] or 0 for r in success), default=0),
            'total_generation_seconds': round(sum(r['final_response_metrics']['duration_seconds'] or 0 for r in success), 4),
            'runtime_fingerprints': dict(runtime_groups), 'safety_evaluation_performed': False}
        summaries.append(summary)
        all_rows[key] = index
        all_errors.extend(model_errors)
        jsonl(out / 'models' / (key + '.jsonl'), [index[sid] for sid in canonical])
        # A short-path JSONL envelope makes imported long Windows filenames unnecessary for downstream readers.
        # The original result dict (including its original run/provenance) is copied without alteration.
        def envelopes():
            for sid in canonical:
                row = index[sid]
                yield {'model_key': key, 'sample_id': sid, 'status': row['status'],
                       'source_path': row['source_path'], 'source_sha256': row['source_sha256'],
                       'source_dataset_path': asset['dataset_path'],
                       'result': read(ROOT / row['source_path']) if row['source_path'] else None,
                       'error_source_paths': row.get('error_source_paths', [])}
        jsonl(out / 'records' / (key + '.jsonl'), envelopes())
    matrix, coverage = [], Counter()
    for sid, record in canonical.items():
        row = {k: record[k] for k in ['sample_id', 'seed_id', 'split', 'condition_id', 'label', 'risk_category']}
        row['models'] = {key: {'status': index[sid]['status'], 'source_path': index[sid]['source_path'],
                              'source_sha256': index[sid]['source_sha256']} for key, index in all_rows.items()}
        matrix.append(row)
        for key, index in all_rows.items():
            r = index[sid]
            coverage[(key, r['split'], r['condition_id'], r['label'], r['visual_schedule'], r['status'])] += 1
    jsonl(out / 'sample_matrix.jsonl', matrix)
    if all_errors:
        originals = out / 'errors/originals'
        originals.mkdir()
        for number, error in enumerate(all_errors, 1):
            copied = originals / (f'{number:03d}-' + re.sub(r'[^A-Za-z0-9_-]', '_', error['error_record']['error_type']) + '.json')
            copied.write_bytes(diskpath(ROOT / error['source_path']).read_bytes())
            if sha(copied) != error['source_sha256']:
                raise ValueError('Error preservation hash differs')
            error['preserved_original_copy'] = copied.relative_to(out).as_posix()
    jsonl(out / 'errors/all_preserved_error_records.jsonl', all_errors)
    dump(out / 'coverage_by_group.json', [dict(zip(['model_key', 'split', 'condition_id', 'label', 'visual_schedule', 'status'], k), count=n)
                                         for k, n in sorted(coverage.items())])
    common = [r['sample_id'] for r in matrix if all(x['status'] == 'model_output_available' for x in r['models'].values())]
    dump(out / 'common_four_model_sample_ids.json', common)
    summary = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'dataset_sha256': dataset_sha,
               'protocol': 'formal_v3_18turn_fixed_reference_only', 'models': summaries,
               'expected_model_sample_cells': 4 * len(canonical), 'common_four_model_samples': len(common),
               'original_result_files_modified': False, 'safety_labels_modified_or_inferred': False,
               'failure_policy': 'Preserve technical failures as unresolved; reproducible OOM does not establish random missingness.'}
    dump(out / 'summary.json', summary)
    dump(out / 'source_runs.json', source_runs)
    dump(out / 'source_files_sha256.json', file_hashes)
    lines = ['# 四模型固定历史结果统一索引', '', '原始结果不移动、不改写；不包含资源闸门或新逐轮生成补测。', '',
             '| 模型 | 成功输出 | 技术失败样本 | 错误记录 | 未解释缺失 | 截断 | 空答 | 高重复启发式 | 确认语回声 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in summaries:
        lines.append(f"| {r['model_key']} | {r['successful_outputs']} | {r['unique_technical_failure_samples']} | {r['preserved_error_records']} | {r['missing_unexplained']} | {r['truncated_final_answers']} | {r['empty_final_answers']} | {r['highly_repetitive_final_answer_heuristic']} | {r['reference_acknowledgment_echo']} |")
    lines += ['', f'四模型共同成功样本：{len(common)}/4864。', '',
        'records/*.jsonl为每模型4864行完整结果信封，原result字典保留run/provenance不改写；技术失败行result=null，不伪造回答。',
        'models/*.jsonl为每模型4864行轻量元数据索引，source_path指向仓库内原文件；sample_matrix.jsonl按同一sample_id对齐四模型。',
        'Gemma原运行、181条补跑和单样本重试保留独立provenance；仅核对配置差异限于选择/运行记账后逻辑合并。',
        'errors/all_preserved_error_records.jsonl保留全部错误正文和堆栈；同一失败样本的多次记录不当作多个独立样本。',
        '报错按实验技术误差/未获得模型回答处理，不计为安全或不安全。该OOM多次复现，不能声称已证明偶然、随机缺失或无偏。',
        '成功输出不等于有效安全判定；空答/截断/重复和API判定故障分开报告。共同成功集合是完整案例子集，不能替代全部面板的缺失报告。',
        '确认语回声=最终模型文本经strip/casefold后与最后一个固定参考assistant文本完全相同；只是可观测文本行为，不自动作为技术错误、安全拒绝或内部机制。',
        'Torch显存数值不是整卡峰值；不同显卡、包版本和输入token化不同，技术指标不是统一硬件速度基准。',
        '本次没有发API、启动GPU或生成新的安全标签。统一索引不修改正在运行的Qwen3评审。', '']
    (out / 'README.md').write_bytes('\n'.join(lines).encode('utf-8'))
    # Recheck every source after collecting; fail rather than publish a silently changed snapshot.
    for name, h in file_hashes.items():
        if sha(ROOT / name) != h:
            raise ValueError('Source changed during collection')
    pointer = out.parent / 'latest.json'
    dump(pointer, {'directory': out.relative_to(ROOT).as_posix(), 'summary_sha256': sha(out / 'summary.json')})
    print(json.dumps({'output': out.relative_to(ROOT).as_posix(), 'models': summaries,
                      'common_four_model_samples': len(common), 'source_hashes_verified': len(file_hashes)}, indent=2))


if __name__ == '__main__':
    main()
