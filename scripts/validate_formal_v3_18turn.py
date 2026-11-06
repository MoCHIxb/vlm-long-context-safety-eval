#!/usr/bin/env python3
"""Independently load saved data, replay random plans and verify full artifacts."""
import argparse
import gzip
import json
import subprocess
import sys
from pathlib import Path
from longvision_eval.controlled_18turn import make_plan,verify_record
from build_formal_v3_18turn import ROOT,load,sha,validate,save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/formal_v3_18turn.json')
    parser.add_argument('--rebuild-check',action='store_true',help='Rebuild and compare dataset, plan and shard hashes')
    args=parser.parse_args()
    config=load(args.config)
    report=load(ROOT/config['report_path'])
    rebuild_verified=False
    previous_versions_unchanged=False
    if args.rebuild_check:
        prior_manifest=load(ROOT/config['shard_directory']/'manifest.json')
        artifacts=[ROOT/config['dataset_path'],ROOT/config['sampling_plan_path'],ROOT/config['shard_directory']/'manifest.json']
        artifacts += [ROOT/s['path'] for s in prior_manifest['shards']]
        protected=[ROOT/config['source_seed_bank'],ROOT/config['original_seed_bank'],ROOT/config['core_acceptance'],
                   ROOT/'data/processed/formal_v3_extended.jsonl']
        before={str(p):sha(p) for p in artifacts+protected if p.is_file()}
        completed=subprocess.run([sys.executable,str(ROOT/'scripts/build_formal_v3_18turn.py'),
                                  '--config',str(args.config)],cwd=ROOT,capture_output=True)
        if completed.returncode:
            raise ValueError('Rebuild process failed; inspect the builder separately')
        if any(sha(p)!=before[str(p)] for p in artifacts):
            raise ValueError('Deterministic rebuild changed an output hash')
        if any(sha(p)!=before[str(p)] for p in protected if str(p) in before):
            raise ValueError('Rebuild changed a protected prior asset')
        rebuild_verified=previous_versions_unchanged=True
        report=load(ROOT/config['report_path'])
    source=ROOT/config['source_seed_bank']
    if sha(args.config)!=report['config_sha256'] or sha(source)!=report['source_seed_bank_sha256']:
        raise ValueError('Input fingerprint mismatch')
    if sha(ROOT/config['dataset_path'])!=report['dataset_sha256'] or sha(ROOT/config['sampling_plan_path'])!=report['sampling_plan_sha256']:
        raise ValueError('Dataset or sampling artifact hash mismatch')
    bank=load(source)
    seeds={s['seed_id']:s for s in bank['harmful']+bank['benign']}
    sampling=load(ROOT/config['sampling_plan_path'])
    if set(sampling['seed_plans'])!=set(seeds):
        raise ValueError('Sampling seed scope mismatch')
    profiles=[{**config['reference_profile'],**p} for p in config['harmful_condition_profiles']]
    capacity=round(max(p['target_context_tokens'] for p in profiles)*0.75)+1500
    streams={}
    for sid,seed in seeds.items():
        expected,stream,_=make_plan(seed,config['global_random_seed'],capacity)
        if expected!=sampling['seed_plans'][sid]:
            raise ValueError('Saved random plan cannot be independently replayed: '+sid)
        streams[sid]=stream
    expected_profiles={p['condition_id']:p for p in profiles}
    expected_profiles.update({p['condition_id']:{'turn_count':18,'risk_position':'none','risk_distribution':'none',
        'modality_relation':'benign_complementary','intent_trajectory':'benign_continuation','factor_under_test':'context_length',**p}
        for p in config['benign_context_profiles']})
    records=[]
    row_hashes={}
    import hashlib
    with (ROOT/config['dataset_path']).open(encoding='utf-8') as f:
        for line in f:
            record=json.loads(line)
            profile=expected_profiles[record['condition_id']]
            if record['variables']!={**profile,'visual_evidence_schedule':record['variables']['visual_evidence_schedule']}:
                raise ValueError('Record variables differ from the configured profile')
            if record['variables']['visual_evidence_schedule'] not in config['visual_evidence_schedules']:
                raise ValueError('Unknown visual schedule')
            sid=record['seed_id']
            verify_record(record,seeds[sid],sampling['seed_plans'][sid],streams[sid],config)
            records.append(record)
            row_hashes[record['sample_id']]=hashlib.sha256(line.encode('utf-8')).hexdigest()
    checks=validate(records,bank,config)
    manifest=load(ROOT/config['shard_directory']/'manifest.json')
    if manifest['dataset_sha256']!=report['dataset_sha256'] or manifest['sampling_plan_sha256']!=report['sampling_plan_sha256']:
        raise ValueError('Shard manifest references a different version')
    seen=set()
    for shard in manifest['shards']:
        path=ROOT/shard['path']
        if sha(path)!=shard['sha256']:
            raise ValueError('Compressed shard hash mismatch')
        count=0
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                row=json.loads(line)
                sid=row['sample_id']
                if sid in seen or hashlib.sha256(line.encode('utf-8')).hexdigest()!=row_hashes.get(sid):
                    raise ValueError('Shards do not partition the exact saved dataset rows')
                seen.add(sid)
                count+=1
        if count!=shard['records']:
            raise ValueError('Shard count mismatch')
    if seen!=set(row_hashes):
        raise ValueError('Missing shard rows')
    result={'status':'independently_verified_saved_artifacts','records':len(records),
            'seed_plans_replayed':len(streams),'shards_verified':len(manifest['shards']),
            'dataset_sha256':report['dataset_sha256'],'sampling_plan_sha256':report['sampling_plan_sha256'],
            'deterministic_rebuild_verified':rebuild_verified,
            'previous_versions_unchanged':previous_versions_unchanged,'checks':checks}
    save(ROOT/'documentation/reports/formal_v3_18turn_validation.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
