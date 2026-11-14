#!/usr/bin/env python3
"""Explicitly execute bounded USTC deepseek-flash-2 review; dry-run is default."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from check_ustc_api import request_json,validate_config
from longvision_eval.dataset import load_json
from longvision_eval.runner import write_json_atomic
from longvision_eval.free_history_supplement import RunLock
from longvision_eval.dialogue_review import load_preparation,evidence_for_job,build_payload,validate_assessment,cached_assessment


def now():return datetime.now(timezone.utc).isoformat()


def execute_job(root,output,manifest,job,client,*,sleep=time.sleep,clock=time.perf_counter):
    evidence=evidence_for_job(root,manifest,job)
    folder=output/'judgments'/job['candidate_id']
    folder.mkdir(parents=True,exist_ok=True)
    payload,metadata=build_payload(root,manifest,job,evidence)
    metadata.update(fingerprint=manifest['fingerprint'],evidence_sha256=job['evidence_sha256'],
        candidate_id=job['candidate_id'],phase=job['phase'])
    config=manifest['config'];calls=0
    for index in range(1,config['max_transport_attempts']+1):
        attempt=folder/f'attempt_{index}'
        if attempt.exists():raise ValueError('Interrupted attempt needs explicit --retry-errors')
        attempt.mkdir();write_json_atomic(attempt/'request_metadata.json',dict(metadata,started_at_utc=now()))
        stage='request';started=clock()
        try:
            calls+=1
            raw=client(config,'/chat/completions',payload)
            write_json_atomic(attempt/'raw_response.json',raw)
            stage='finish_reason';choice=raw.get('choices',[{}])[0]
            if choice.get('finish_reason')!='stop' or choice.get('message',{}).get('refusal'):
                raise ValueError('Nonfinal or refused judge response')
            stage='json_parse';assessment=json.loads(choice['message']['content'])
            stage='validation';validate_assessment(assessment,evidence)
            # Provenance precedes labels: interrupted writes never form a cache hit.
            data=(json.dumps(assessment,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
            write_json_atomic(folder/'provenance.json',dict(metadata,assessment_sha256=hashlib.sha256(data).hexdigest(),
                returned_model=raw.get('model'),usage=raw.get('usage'),label_source='machine_unreviewed',
                elapsed_seconds=round(clock()-started,3),attempts=index))
            (folder/'assessment.json').write_bytes(data)
            return True,calls,False
        except Exception as error:
            status=error.code if isinstance(error,urllib.error.HTTPError) else None
            transient=stage=='request' and (status in (408,429,500,502,503,504) or
                (status is None and isinstance(error,(TimeoutError,urllib.error.URLError))))
            failure=dict(error_type=type(error).__name__,http_status=status,stage=stage,
                elapsed_seconds=round(clock()-started,3),automatic_retry=bool(transient and index<config['max_transport_attempts']))
            write_json_atomic(attempt/'failure.json',failure)
            if transient and index<config['max_transport_attempts']:
                sleep(config['rate_limit_cooldown_seconds'] if status==429 else max(config['request_spacing_seconds'],2**index))
                continue
            write_json_atomic(folder/'judge_failure.json',failure)
            return False,calls,status in (401,402,403)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',required=True,type=Path)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--limit',type=int,default=8,help='Maximum uncached jobs this invocation, not trajectories')
    p.add_argument('--retry-errors',action='store_true',help='Explicitly archive failed/interrupted jobs; valid labels are never regenerated')
    args=p.parse_args()
    output=(ROOT/args.bundle).resolve();manifest=load_preparation(ROOT,output);config=manifest['config']
    validate_config(config)
    if config['model']!='deepseek-flash-2':raise ValueError('This protocol pins deepseek-flash-2')
    if not 1<=args.limit<=config['max_requests_per_invocation']:p.error('Invalid request limit')
    print(json.dumps(dict(prepared_jobs=len(manifest['jobs']),execute=args.execute,
        new_job_limit=args.limit,maximum_transport_calls=args.limit*config['max_transport_attempts'],
        raw_evidence_sent_only_on_execute=True,network_requests=0)),flush=True)
    if not args.execute:return 0
    if manifest.get('synthetic'):raise ValueError('Synthetic preparations cannot be used as real evidence')
    if not os.environ.get(config['api_key_env'],'').strip():raise ValueError('Set USTC_LLM_API_KEY in this terminal')
    with RunLock(output/'execution.lock'):
        state=dict(status='running',pid=os.getpid(),fingerprint=manifest['fingerprint'],
            network_requests_this_invocation=0,new_valid_this_invocation=0,label_source='machine_unreviewed',started_at_utc=now())
        def progress(**changes):
            state.update(changes,updated_at_utc=now());write_json_atomic(output/'progress.json',state)
        done=failures=selected=consecutive=0;last_request=None
        try:
            progress()
            for job in manifest['jobs']:
                folder=output/'judgments'/job['candidate_id']
                evidence=evidence_for_job(ROOT,manifest,job)
                if cached_assessment(folder,job,evidence,manifest['fingerprint']) is not None:
                    done+=1;continue
                if folder.exists():
                    if not args.retry_errors:
                        failures+=1;continue
                    archive=output/'error_history'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                    archive.mkdir(parents=True);folder.rename(archive/job['candidate_id'])
                if selected>=args.limit:continue
                selected+=1
                if last_request is not None:time.sleep(max(0,config['request_spacing_seconds']-(time.monotonic()-last_request)))
                last_request=time.monotonic()
                ok,calls,fatal=execute_job(ROOT,output,manifest,job,request_json)
                done+=ok;failures+=not ok;consecutive=0 if ok else consecutive+1
                progress(candidate_id=job['candidate_id'],phase=job['phase'],valid_jobs=done,failed_jobs=failures,
                    network_requests_this_invocation=state['network_requests_this_invocation']+calls,
                    new_valid_this_invocation=state['new_valid_this_invocation']+int(ok))
                print(json.dumps(dict(valid=done,failures=failures,total=len(manifest['jobs']),phase=job['phase'])),flush=True)
                if fatal or consecutive>=config['stop_after_consecutive_failures']:
                    progress(status='stopped_needs_attention',pid=None);return 2
            status='complete' if done==len(manifest['jobs']) else ('complete_with_failures' if done+failures==len(manifest['jobs']) else 'partial')
            progress(status=status,pid=None,valid_jobs=done,failed_jobs=failures)
            return 0 if not failures else 2
        except KeyboardInterrupt:
            progress(status='paused_by_user',pid=None);return 130
        except Exception as error:
            progress(status='stopped_needs_attention',pid=None,error_type=type(error).__name__);raise


if __name__=='__main__':raise SystemExit(main())
