#!/usr/bin/env python3
"""Prepare a shared formal panel and serial four-model queue; no inference."""
import hashlib
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=value:
        raise ValueError('Refusing to overwrite a different run configuration: '+str(path))
    if not path.exists():
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-new-tokens',type=int,default=1024)
    args=parser.parse_args()
    if args.max_new_tokens<=0:
        parser.error('max-new-tokens must be positive')
    report=json.loads((ROOT/'documentation/reports/formal_v3_18turn_status.json').read_text(encoding='utf-8'))
    dataset=ROOT/report['dataset']
    if sha(dataset)!=report['dataset_sha256']:
        raise ValueError('Dataset hash mismatch')
    records=[json.loads(line) for line in dataset.open(encoding='utf-8')]
    if len(records)!=4864:
        raise ValueError('Unexpected formal panel size')
    calibration=[r for r in records if r['split']=='calibration']
    categories=sorted({r['risk_category'] for r in calibration if r['track']=='harmful_controlled'})
    seeds=[min(r['seed_id'] for r in calibration if r['risk_category']==cat) for cat in categories]
    ids=[]
    def add(sid,cid,schedule,label):
        row=next(r for r in calibration if r['seed_id']==sid and r['condition_id']==cid
                 and r['variables']['visual_evidence_schedule']==schedule and r['label']==label)
        ids.append(row['sample_id'])
    for sid in seeds:
        add(sid,'C04','static_initial_bundle','unsafe')
        add(sid,'C04','dynamic_incremental','safe')
    for cid in ('C03','C13'):
        add(seeds[0],cid,'static_initial_bundle','unsafe')
        add(seeds[0],cid,'dynamic_incremental','safe')
    benign=min(r['seed_id'] for r in calibration if r['track']=='benign_controlled')
    for cid in ('B02','B16'):
        for schedule in ('static_initial_bundle','dynamic_incremental'):
            add(benign,cid,schedule,'safe')
    code_paths=('src/longvision_eval/runner.py','src/longvision_eval/provenance.py',
        'src/longvision_eval/dataset.py','src/longvision_eval/models/__init__.py',
        'src/longvision_eval/models/base.py','src/longvision_eval/models/qwen_transformers.py')
    fingerprints={p:sha(ROOT/p) for p in code_paths}
    code_tag=hashlib.sha256(json.dumps(fingerprints,sort_keys=True).encode()).hexdigest()[:8]
    models=json.loads((ROOT/'configs/deployment/open_models.json').read_text(encoding='utf-8'))['models']
    queue={'dataset_path':report['dataset'],'dataset_sha256':report['dataset_sha256'],
           'sample_count_per_model':4864,'total_formal_samples':19456,
           'history_mode':'fixed_reference','serial_models':True,'max_new_tokens':args.max_new_tokens,'models':[]}
    for model in models:
        key=model['key']
        model_path=f'configs/models/formal_18turn/{key}_nf4.json'
        save(ROOT/model_path,model)
        paths={}
        for stage in ('gate','formal'):
            run_id=f'{stage}-v318-{key}-{report["dataset_sha256"][:8]}-{code_tag}-g{args.max_new_tokens}'
            config={'run_id':run_id,'experiment_stage':'resource_gate_18turn' if stage=='gate' else 'formal_18turn',
                'human_review_status':'original_core_accepted_by_user_api_extensions_integrated',
                'model_config':model_path,'dataset_path':report['dataset'],
                'expected_dataset_sha256':report['dataset_sha256'],'expected_code_sha256':fingerprints,
                'output_dir':'outputs/formal_v3_18turn_runs','history_mode':'fixed_reference',
                'stop_on_error':True,'generation':{'max_new_tokens':args.max_new_tokens,'do_sample':False,'repetition_penalty':1.05}}
            if stage=='gate':
                config['sample_ids']=ids
            path=f'configs/runs/formal_v3_18turn/{run_id}.json'
            save(ROOT/path,config)
            paths[stage]=path
        queue['models'].append({'key':key,'model_config':model_path,**paths})
    queue_path=f'configs/runs/formal_v3_18turn/queue-{report["dataset_sha256"][:8]}-{code_tag}-g{args.max_new_tokens}.json'
    save(ROOT/queue_path,queue)
    print(json.dumps({'queue':queue_path,'formal_samples_per_model':4864,
                      'gate_samples_per_model':len(ids),'model_order':[m['key'] for m in queue['models']]},indent=2))


if __name__=='__main__':
    main()
