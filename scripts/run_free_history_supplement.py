#!/usr/bin/env python3
"""Prepare or run one model's independent generated-history turn-count supplement."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from longvision_eval.dataset import load_json
from longvision_eval.runner import write_json_atomic
from longvision_eval.free_history_supplement import prepare, RunLock, run_trajectory, summarize, verify_artifact


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, choices=['qwen25vl7b', 'qwen3vl8b', 'llava7b', 'gemma3_12b'])
    parser.add_argument('--site', required=True, help='Distinct machine identifier, e.g. local5070ti or cloud3090a')
    parser.add_argument('--stage', choices=['gate', 'formal', 'all'], default='all')
    parser.add_argument('--execute', action='store_true', help='Without this flag, only prepare/validate; no GPU or model load')
    parser.add_argument('--retry-errors', action='store_true', help='Explicitly archive prior failed attempts, retaining committed turns')
    args = parser.parse_args()
    os.environ.update(HF_HOME=str(ROOT / '.cache/huggingface'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    protocol, model, records, gate, output, fingerprint = prepare(ROOT, ROOT / 'configs/free_history_supplement_v1.json', args.model, args.site)
    print(json.dumps({'prepared': output.relative_to(ROOT).as_posix(), 'formal_trajectories': len(records),
                      'formal_model_calls': sum(len(r['turns']) for r in records), 'gate_trajectories': len(gate),
                      'execute': args.execute, 'other_models_will_start': False}), flush=True)
    if not args.execute:
        return 0
    if (ROOT / 'outputs/formal_v3_18turn_runs/serial_queue.lock').exists():
        raise RuntimeError('An existing formal GPU queue lock exists; inspect its owner, do not delete blindly')
    with RunLock(ROOT / 'outputs/free_history_supplement/.gpu_model.lock'):
        progress_path = output / 'progress.json'
        state = {'status': 'starting', 'model': args.model, 'site': args.site, 'fingerprint': fingerprint,
                 'pid': os.getpid(), 'created_at_utc': now(), 'history_mode': protocol['history_mode']}

        def progress(**changes):
            state.update(changes, updated_at_utc=now())
            write_json_atomic(progress_path, state)

        adapter = None
        try:
            stages = [('gate', gate)] if args.stage == 'gate' else [('gate', gate), ('formal', records)]
            for stage, panel in stages:
                directory = output / stage
                directory.mkdir(exist_ok=True)
                errors = directory / 'errors'
                errors.mkdir(exist_ok=True)
                progress(stage=stage, status='validating_existing', complete=False,
                         planned_trajectories=len(panel), completed_trajectories=0)
                # Validate all committed results and checkpoints before loading weights.
                summary = summarize(directory, panel, fingerprint, ROOT)
                if summary['complete']:
                    progress(stage=stage, status='stage_complete', completed_trajectories=summary['completed'], **summary)
                    continue
                for record in panel:
                    error = errors / (record['sample_id'] + '.json')
                    if error.exists():
                        if not args.retry_errors:
                            raise RuntimeError('Saved failure needs explicit --retry-errors: ' + record['sample_id'])
                        archive = directory / 'error_history' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                        archive.mkdir(parents=True)
                        error.rename(archive / error.name)
                if adapter is None:
                    progress(stage=stage, status='loading_model')
                    from longvision_eval.models import create_adapter
                    adapter = create_adapter(model)
                    runtime = adapter.runtime_info()
                    runtime_path = output / 'runtime.json'
                    if runtime_path.exists() and load_json(runtime_path) != runtime:
                        raise ValueError('Model runtime/device map changed; use another site/run version')
                    write_json_atomic(runtime_path, runtime)
                committed = summary['committed_model_calls']
                completed = summary['completed']
                for record in panel:
                    result = directory / (record['sample_id'] + '.json')
                    if result.exists():
                        continue
                    sid = record['sample_id']

                    def on_turn(index, total, response):
                        nonlocal committed
                        committed += 1
                        progress(stage=stage, status='running', sample_id=sid, turn_index=index, turn_count=total,
                                 completed_trajectories=completed, planned_trajectories=len(panel),
                                 committed_model_calls=committed, last_input_tokens=response.get('input_tokens'),
                                 last_output_tokens=response.get('output_tokens'), last_truncated=response.get('truncated'))

                    try:
                        run_trajectory(record, adapter, protocol['generation'], ROOT, directory, fingerprint, on_turn)
                    except Exception as error:
                        write_json_atomic(errors / (sid + '.json'), {'sample_id': sid, 'error_type': type(error).__name__,
                            'error_message': str(error), 'traceback': traceback.format_exc(), 'created_at_utc': now(),
                            'fingerprint': fingerprint, 'checkpoint_retained': True, 'automatic_retry': False})
                        raise
                    completed += 1
                    print(json.dumps({'stage': stage, 'completed': completed, 'target': len(panel), 'sample_id': sid}), flush=True)
                summary = summarize(directory, panel, fingerprint, ROOT)
                progress(stage=stage, status='stage_complete', completed_trajectories=summary['completed'], **summary)
                if not summary['complete']:
                    raise RuntimeError('Stage incomplete; do not advance')
            progress(status='complete', pid=None, finished_at_utc=now())
            print(json.dumps({'status': 'complete', 'output': output.relative_to(ROOT).as_posix(),
                              'human_or_api_evaluation_performed': False}), flush=True)
            return 0
        except KeyboardInterrupt:
            progress(status='paused_by_user', pid=None, checkpoint_retained=True)
            return 130
        except Exception as error:
            progress(status='stopped_needs_attention', pid=None, error_type=type(error).__name__, detail=str(error))
            print(json.dumps({'status': state['status'], 'error_type': type(error).__name__, 'detail': str(error)}), flush=True)
            return 2


if __name__ == '__main__':
    raise SystemExit(main())
