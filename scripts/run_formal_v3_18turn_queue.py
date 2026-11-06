#!/usr/bin/env python3
"""Serial offline four-model gate/full run queue. Never loads two models at once."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from longvision_eval.runner import write_json_atomic
from longvision_eval.run_metrics import summarize_runs

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'outputs/formal_v3_18turn_runs'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def now():
    return datetime.now(timezone.utc).isoformat()


def free_gpu():
    value=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
                         check=True,capture_output=True,text=True)
    return int(value.stdout.splitlines()[0].strip())


def quality(directory):
    flags={'empty_final_answers':0,'highly_repetitive_final_answers':0,'result_count':0}
    for path in directory.glob('V318-*.json'):
        result=load(path)
        text=result['turns'][-1]['response']['text']
        flags['result_count']+=1
        flags['empty_final_answers']+=not text.strip()
        words=re.findall(r'\w+',text.lower())
        if len(words)>=40:
            grams=[tuple(words[i:i+3]) for i in range(len(words)-2)]
            flags['highly_repetitive_final_answers']+=len(set(grams))/len(grams)<0.15
    return flags


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    args=parser.parse_args()
    plan=load((ROOT/args.plan).resolve())
    OUTPUT.mkdir(parents=True,exist_ok=True)
    log_dir=OUTPUT/'logs'
    log_dir.mkdir(exist_ok=True)
    lock=OUTPUT/'serial_queue.lock'
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(descriptor,str(os.getpid()).encode())
    os.close(descriptor)
    env=os.environ.copy()
    env.update(HF_HOME=str(ROOT/'.cache/huggingface'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
               PYTHONPATH=str(ROOT/'src'),PYTHONUTF8='1',PYTHONUNBUFFERED='1')
    state={'status':'running','pid':os.getpid(),'plan':str(args.plan),
           'dataset_sha256':plan['dataset_sha256'],'models':plan['models'],
           'formal_samples_per_model':plan['sample_count_per_model'],
           'completed_models':[],'started_at_utc':now()}
    status_path=OUTPUT/'queue_status.json'
    def status(**changes):
        state.update(changes,updated_at_utc=now())
        write_json_atomic(status_path,state)
    def child(arguments,log_name,progress_dir=None):
        path=log_dir/log_name
        with path.open('a',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,*arguments],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            status(child_pid=process.pid,log=str(path.relative_to(ROOT)))
            while process.poll() is None:
                if progress_dir:
                    status(results_written=len(list(progress_dir.glob('V318-*.json'))),
                           error_files=len(list((progress_dir/'errors').glob('*.json'))))
                time.sleep(10)
            status(child_pid=None)
            if process.returncode:
                raise RuntimeError('Child stage failed; inspect '+str(path.relative_to(ROOT)))
    try:
        # Processor checks are CPU-only. Finish them before starting any formal model run.
        for item in plan['models']:
            key=item['key']
            status(model=key,phase='cpu_gate_input_preflight',results_written=0,error_files=0)
            print(key+': CPU input-budget preflight',flush=True)
            child(['scripts/preflight_formal_v3_18turn.py','--config',item['gate']],key+'-preflight.log')
            preflight=load(OUTPUT/'preflight'/f'{key}.json')
            if not preflight['passed']:
                raise RuntimeError('CPU gate input preflight did not pass: '+key)
        for item in plan['models']:
            key=item['key']
            model=load(ROOT/item['model_config'])
            while free_gpu()<model['minimum_free_gpu_mib']:
                status(status='waiting_for_gpu',model=key,phase='waiting_for_gpu',free_gpu_mib=free_gpu())
                time.sleep(30)
            status(status='running',model=key,phase='synthetic_gpu_smoke')
            deployment_path=ROOT/'outputs/model_deployment'/f'{key}.json'
            previous=load(deployment_path) if deployment_path.exists() else {}
            fresh=previous.get('updated_at_utc','')[:10]==now()[:10]
            if not (fresh and previous.get('revision')==model['revision'] and previous.get('smoke_check',{}).get('passed')):
                print(key+': synthetic GPU smoke',flush=True)
                child(['scripts/prepare_open_models.py','--model',key,'--smoke'],key+'-smoke.log')
                previous=load(deployment_path)
                if not previous.get('smoke_check',{}).get('passed'):
                    raise RuntimeError('Synthetic generation did not pass: '+key)
            for stage in ('gate','formal'):
                run=load(ROOT/item[stage])
                directory=ROOT/run['output_dir']/run['run_id']
                expected=len(run.get('sample_ids',[])) if stage=='gate' else plan['sample_count_per_model']
                status(model=key,phase=stage,run_id=run['run_id'],run_dir=str(directory.relative_to(ROOT)),
                       expected_results=expected,results_written=0,error_files=0)
                print(key+': starting '+stage+' ('+str(expected)+' samples)',flush=True)
                child(['scripts/run_experiment.py','--config',item[stage],'--resume'],key+'-'+stage+'.log',directory)
                metrics=summarize_runs([directory])
                technical=quality(directory)
                metrics['technical_quality_flags']=technical
                write_json_atomic(directory/'technical_metrics.json',metrics)
                if metrics['sample_count']!=expected or metrics['error_file_count']:
                    raise RuntimeError('Incomplete '+stage+' run: '+key)
                if technical['empty_final_answers'] or technical['highly_repetitive_final_answers']>max(1,expected//4):
                    raise RuntimeError('Generation quality gate needs attention: '+key)
                status(last_completed_stage=stage,last_technical_metrics=metrics)
                print(key+': '+stage+' complete',flush=True)
            state['completed_models'].append(key)
            status()
        status(status='complete',phase=None,model=None,finished_at_utc=now())
        print('Four-model formal queue complete.',flush=True)
        return 0
    except Exception as error:
        status(status='stopped_on_error',error_type=type(error).__name__,detail=str(error))
        print(json.dumps({k:state.get(k) for k in ('status','model','phase','detail','log')},indent=2),flush=True)
        return 1
    finally:
        lock.unlink(missing_ok=True)


if __name__=='__main__':
    sys.exit(main())
