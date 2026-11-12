#!/usr/bin/env python3
"""Run ONLY Qwen3's actual-assistant supplement, with resumable per-turn checkpoints."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from longvision_eval.dataset import load_json
from longvision_eval.runner import write_json_atomic
from longvision_eval.free_history_supplement import RunLock, run_trajectory, summarize, history_digest
from longvision_eval.real_dialogue_supplement import prepare, export_trajectory


def now():
    return datetime.now(timezone.utc).isoformat()


class AttemptRecorder:
    """Retain uncommitted empty-output telemetry without changing the executor."""
    def __init__(self, adapter):
        self.adapter=adapter
        self.last_attempt=None

    def generate(self, messages, generation):
        self.last_attempt=dict(turn_index=sum(m['role']=='user' for m in messages),
            input_history_sha256=history_digest(messages,ROOT),response=None)
        result=self.adapter.generate(messages,generation)
        self.last_attempt['response']=result.to_dict()
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',required=True,help='Stable server ID; use the same value to resume')
    parser.add_argument('--stage',choices=['gate','calibration','primary','heldout','all'],default='gate')
    parser.add_argument('--execute',action='store_true',help='Without this flag: validate and plan only; never load a model')
    parser.add_argument('--retry-errors',action='store_true',help='Archive saved errors and explicitly retry from last complete response')
    args=parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    os.environ.setdefault('HF_HOME',str(ROOT/'.cache/huggingface'))
    config, model, records, gate, output, fingerprint=prepare(ROOT,ROOT/'configs/real_dialogue_supplement_qwen3_v1.json',args.site)
    stages=[('gate',gate)]
    splits=['calibration','primary','heldout'] if args.stage=='all' else ([] if args.stage=='gate' else [args.stage])
    stages.extend((split,[r for r in records if r['split']==split]) for split in splits)
    requested={r['sample_id']:r for _,panel in stages for r in panel}
    print(json.dumps(dict(prepared=output.relative_to(ROOT).as_posix(),model='qwen3vl8b',
        stage=args.stage,execute=args.execute,unique_requested_trajectories=len(requested),
        requested_model_calls=sum(len(r['turns']) for r in requested.values()),
        entire_panel_trajectories=len(records),entire_panel_model_calls=sum(len(r['turns']) for r in records),
        gate_included_in_calibration=True,other_models_will_start=False)),flush=True)
    if not args.execute:
        return 0
    if (ROOT/'outputs/formal_v3_18turn_runs/serial_queue.lock').exists():
        raise RuntimeError('Original formal GPU queue lock exists; inspect its owner before starting this separate run')
    # Shares the already deployed free-history lock so two supplement processes
    # cannot consume the same checkout's GPU simultaneously.
    with RunLock(ROOT/'outputs/free_history_supplement/.gpu_model.lock'):
        state=dict(status='starting',pid=os.getpid(),model='qwen3vl8b',fingerprint=fingerprint,created_at_utc=now())
        def progress(**changes):
            state.update(changes,updated_at_utc=now())
            write_json_atomic(output/'progress.json',state)
        adapter=None
        try:
            for stage,panel in stages:
                # Gate is a subset of calibration, with exactly the same record
                # hashes and directory; never duplicate its 80 generation calls.
                directory=output/('calibration' if stage=='gate' else stage)
                directory.mkdir(exist_ok=True)
                errors=directory/'errors'
                errors.mkdir(exist_ok=True)
                progress(stage=stage,status='validating_existing',planned_trajectories=len(panel))
                stats=summarize(directory,panel,fingerprint,ROOT)
                for record in panel:
                    error=errors/(record['sample_id']+'.json')
                    if error.exists():
                        if not args.retry_errors:
                            raise RuntimeError('Saved failure requires inspection and explicit --retry-errors: '+record['sample_id'])
                        archive=directory/'error_history'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                        archive.mkdir(parents=True)
                        error.rename(archive/error.name)
                committed=stats['committed_model_calls']
                completed=stats['completed']
                for record in panel:
                    result_path=directory/(record['sample_id']+'.json')
                    if result_path.exists():
                        export_trajectory(ROOT,record,load_json(result_path),output,fingerprint)
                        continue
                    if adapter is None:
                        progress(status='loading_model')
                        from longvision_eval.models import create_adapter
                        adapter=create_adapter(model)
                        runtime=adapter.runtime_info()
                        runtime_path=output/'runtime.json'
                        if runtime_path.exists() and load_json(runtime_path)!=runtime:
                            raise ValueError('Actual model runtime/device map changed; do not mix with this run')
                        write_json_atomic(runtime_path,runtime)
                    sid=record['sample_id']
                    def on_turn(index,total,response):
                        nonlocal committed
                        committed+=1
                        progress(status='running',sample_id=sid,turn_index=index,turn_count=total,
                            completed_trajectories=completed,committed_model_calls=committed,
                            last_input_tokens=response.get('input_tokens'),last_output_tokens=response.get('output_tokens'),
                            last_truncated=response.get('truncated'))
                        print(json.dumps(dict(stage=stage,sample_id=sid,turn=index,total=total,
                            completed=completed,target=len(panel))),flush=True)
                    attempt=AttemptRecorder(adapter)
                    try:
                        payload=run_trajectory(record,attempt,config['generation'],ROOT,directory,fingerprint,on_turn)
                        export_trajectory(ROOT,record,payload,output,fingerprint)
                    except Exception as error:
                        write_json_atomic(errors/(sid+'.json'),dict(sample_id=sid,error_type=type(error).__name__,
                            error_message=str(error),traceback=traceback.format_exc(),fingerprint=fingerprint,
                            created_at_utc=now(),checkpoint_retained=True,automatic_retry=False,
                            last_attempt=attempt.last_attempt))
                        raise
                    completed+=1
                stats=summarize(directory,panel,fingerprint,ROOT)
                write_json_atomic(output/(stage+'_technical_summary.json'),stats)
                if not stats['complete']:
                    raise RuntimeError('Stage is incomplete; refusing to advance: '+stage)
                progress(status='stage_complete',stage=stage,completed_trajectories=completed)
            progress(status='complete',pid=None,finished_at_utc=now(),assessment_performed=False)
            print(json.dumps(dict(status='complete',stage=args.stage,output=output.relative_to(ROOT).as_posix(),
                                  human_or_api_assessment_performed=False)),flush=True)
            return 0
        except KeyboardInterrupt:
            progress(status='paused_by_user',pid=None,checkpoint_retained=True)
            return 130
        except Exception as error:
            progress(status='stopped_needs_attention',pid=None,error_type=type(error).__name__,detail=str(error))
            print(json.dumps(dict(status=state['status'],error_type=type(error).__name__,detail=str(error))),flush=True)
            return 2


if __name__=='__main__':
    raise SystemExit(main())
