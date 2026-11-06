#!/usr/bin/env python3
"""Build and verify the18-turn protocol without API requests or model loading."""
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path

from longvision_eval.controlled_18turn import build_group,digest,make_plan,verify_record
from validate_formal_v3 import validate_seed_bank

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


def history(record):
    return [(t['user']['content'],t['assistant_context']) for t in record['turns']]


def images(record):
    return [im for t in record['turns'] for im in t['user']['images']]


def validate(records,bank,config):
    expected=config['expected_sizes']
    if len(records)!=expected['total_trajectories'] or len({r['sample_id'] for r in records})!=len(records):
        raise ValueError('Dataset scale or sample uniqueness failed')
    groups=defaultdict(list)
    goals=defaultdict(list)
    schedules=defaultdict(list)
    per_seed=defaultdict(dict)
    for r in records:
        groups[(r['seed_id'],r['condition_id'])].append(r)
        if r['pair_id']:
            goals[r['pair_id']].append(r)
        schedules[r['schedule_pair_id']].append(r)
        per_seed[r['seed_id']][r['condition_id']]=r
        if len(images(r))!=len(set(images(r))) or not all((ROOT/p).is_file() for p in images(r)):
            raise ValueError('Image existence or uniqueness failed')
    if len(goals)!=expected['safe_unsafe_pairs'] or len(schedules)!=expected['visual_schedule_pairs']:
        raise ValueError('Pair scale failed')
    for pair in goals.values():
        a,b=pair
        if {a['label'],b['label']}!={'safe','unsafe'} or history(a)[:-1]!=history(b)[:-1] or images(a)!=images(b):
            raise ValueError('Safe/unsafe matching failed')
    for pair in schedules.values():
        a,b=pair
        if history(a)!=history(b) or images(a)!=images(b):
            raise ValueError('Visual matching failed')
        static=next(r for r in pair if r['variables']['visual_evidence_schedule']=='static_initial_bundle')
        dynamic=next(r for r in pair if r['variables']['visual_evidence_schedule']=='dynamic_incremental')
        if static['turns'][0]['user']['images']!=images(static) or not any(t['user']['images'] for t in dynamic['turns'][1:]):
            raise ValueError('Visual schedule placement failed')
    max_mean=max_individual=0.0
    for members in groups.values():
        target=members[0]['variables']['target_context_tokens']
        actual=[r['context_stats']['estimated_tokens'] for r in members]
        max_mean=max(max_mean,abs(sum(actual)/len(actual)-target)/target)
        max_individual=max(max_individual,max(abs(v-target)/target for v in actual))
    if max_mean>config['length_control']['paired_mean_relative_tolerance']:
        raise ValueError('Nominal paired-mean length tolerance failed: '+str(max_mean))
    for seed in bank['harmful']:
        rows=per_seed[seed['seed_id']]
        contrasts=('C00','C05','C06','C07','C08')
        if len({rows[c]['construction']['neutral_content_sha256'] for c in contrasts})!=1:
            raise ValueError('Position/distribution accidentally randomized neutral context')
        turns=('C01','C02','C00','C12','C13')
        if {rows[c]['variables']['turn_count'] for c in turns}!={6,12,18,24,30}:
            raise ValueError('Missing turn-count level')
        if len({rows[c]['construction']['neutral_content_sha256'] for c in turns})!=1:
            raise ValueError('Turn-count contrast changed neutral text rather than repartitioning it')
        if not rows['C03']['construction']['neutral_prefix_units']<=rows['C00']['construction']['neutral_prefix_units']<=rows['C04']['construction']['neutral_prefix_units']:
            raise ValueError('Length prefixes are not nested')
        for c in ('C03','C04','C05','C06','C07','C08','C09','C10','C11'):
            if rows[c]['variables']['turn_count']!=18:
                raise ValueError('Non-turn factor changed reference turn count')
        for c in ('C05','C06','C07','C08'):
            if rows[c]['variables']['target_context_tokens']!=8192:
                raise ValueError('Position/distribution changed length budget')
        for c in ('C00','C07','C08'):
            events=rows[c]['construction']['core_placements']
            positions=[e['turn_index'] for e in events if e['field'] in {'latent_cue','escalating_cue'}]
            if sum(positions)/2!=config['risk_placement_18turn']['distribution_center_turn']:
                raise ValueError('Distribution contrast shifted risk center')
    for seed in bank['benign']:
        rows=per_seed[seed['seed_id']]
        if not all(r['variables']['turn_count']==18 for r in rows.values()):
            raise ValueError('Unexpected benign turn-count cross-product')
        if not rows['B02']['construction']['neutral_prefix_units']<=rows['B08']['construction']['neutral_prefix_units']<=rows['B16']['construction']['neutral_prefix_units']:
            raise ValueError('Benign length prefixes are not nested')
    return {'max_paired_mean_estimated_relative_deviation':max_mean,
            'max_individual_estimated_relative_deviation':max_individual,
            'safe_unsafe_pairs':len(goals),'visual_schedule_pairs':len(schedules),
            'opening_and_final_protected':True,'all_nonfinal_histories_fixed_and_nonempty':True,
            'position_distribution_neutral_multiset_identical':True,
            'turn_count_neutral_multiset_identical':True,'length_prefixes_nested':True,
            'actual_model_input_budgets_verified':False}


def build(config):
    source=ROOT/config['source_seed_bank']
    if sha(source)!=config['source_seed_bank_sha256']:
        raise ValueError('Source pool changed; use an explicitly versioned configuration')
    bank=load(source)
    original=ROOT/config['original_seed_bank']
    acceptance=load(ROOT/config['core_acceptance'])
    if sha(original)!=acceptance['original_seed_bank_sha256']:
        raise ValueError('Accepted original core hash changed')
    if sha(original)!=config['accepted_original_seed_bank_sha256']:
        raise ValueError('Configuration references a different accepted core')
    originals=load(original)
    indexed={s['seed_id']:s for s in originals['harmful']+originals['benign']}
    if (acceptance.get('status')!='original_core_accepted_by_user' or acceptance.get('core_accepted_count')!=144
            or set(acceptance.get('accepted_seed_ids',[]))!=set(indexed)):
        raise ValueError('Explicit acceptance does not cover the full source seed set')
    validate_seed_bank(bank,load(ROOT/'configs/formal_v3_taxonomy.json'))
    profiles=[{**config['reference_profile'],**p} for p in config['harmful_condition_profiles']]
    records=[]
    sampling={'schema_version':config['schema_version'],'global_random_seed':config['global_random_seed'],
              'source_seed_bank_sha256':sha(source),'seed_plans':{}}
    capacity=round(max(p['target_context_tokens'] for p in profiles)*0.75)+1500
    for seed in bank['harmful']+bank['benign']:
        original_seed=indexed[seed['seed_id']]
        fields=('neutral_setup','latent_cue','escalating_cue','safe_final_request','unsafe_final_request')
        if seed['scene_type']=='harmful':
            if any(seed['dialogue_atoms'][f]!=original_seed['dialogue_atoms'][f] for f in fields):
                raise ValueError('Original core was rewritten')
            selected=profiles
        else:
            if seed['dialogue_outline']!=original_seed['dialogue_outline'] or seed['final_request']!=original_seed['final_request']:
                raise ValueError('Original benign core changed')
            selected=[{'turn_count':18,'risk_position':'none','risk_distribution':'none',
                       'modality_relation':'benign_complementary','intent_trajectory':'benign_continuation',
                       'factor_under_test':'context_length',**p} for p in config['benign_context_profiles']]
        plan,stream,prefix_words=make_plan(seed,config['global_random_seed'],capacity)
        sampling['seed_plans'][seed['seed_id']]=plan
        for profile in selected:
            group=build_group(seed,profile,config,stream,prefix_words)
            for record in group:
                verify_record(record,seed,plan,stream,config)
            records.extend(group)
    validation=validate(records,bank,config)
    return records,sampling,validation,sha(source),sha(original)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/formal_v3_18turn.json')
    args=parser.parse_args()
    config=load(args.config)
    if config['dataset_path'] in {'data/processed/formal_v3.jsonl','data/processed/formal_v3_extended.jsonl'}:
        raise ValueError('The18-turn build must not overwrite preserved versions')
    records,sampling,validation,source_sha,original_sha=build(config)
    output=ROOT/config['dataset_path']
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.jsonl.tmp')
    with temporary.open('w',encoding='utf-8',newline='\n') as f:
        for record in records:
            f.write(json.dumps(record,ensure_ascii=False)+'\n')
    temporary.replace(output)
    save(ROOT/config['sampling_plan_path'],sampling)
    directory=ROOT/config['shard_directory']
    directory.mkdir(parents=True,exist_ok=True)
    grouped=defaultdict(list)
    for r in records:
        grouped[r['risk_category'] if r['track']=='harmful_controlled' else 'benign'].append(r)
    shards=[]
    for name,items in sorted(grouped.items()):
        path=directory/(name+'.jsonl.gz')
        with path.open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz:
                for item in items:
                    gz.write((json.dumps(item,ensure_ascii=False)+'\n').encode('utf-8'))
        shards.append({'path':path.relative_to(ROOT).as_posix(),'records':len(items),'sha256':sha(path)})
    report={'status':'built_and_structurally_verified_18turn_protocol','independent_seeds':144,
            'trajectory_count':len(records),'track_counts':dict(Counter(r['track'] for r in records)),
            'condition_counts':dict(Counter(r['condition_id'] for r in records)),
            'turn_counts':dict(Counter(r['variables']['turn_count'] for r in records)),
            'config_sha256':sha(args.config),'source_seed_bank_sha256':source_sha,
            'accepted_original_seed_bank_sha256':original_sha,'core_acceptance':config['core_acceptance'],
            'dataset':config['dataset_path'],'dataset_bytes':output.stat().st_size,'dataset_sha256':sha(output),
            'sampling_plan':config['sampling_plan_path'],'sampling_plan_sha256':sha(ROOT/config['sampling_plan_path']),
            'validation':validation,'api_requests':0,'gpu_used':False,'models_run':False,
            'protocol_notes':['Reference assistant responses standardized to Noted.; all actual user cores preserved.',
                              'Benign scope remains length x visual schedule at18 turns.',
                              'Length targets are nominal word estimates, not measured multimodal model token budgets.',
                              'C09/C10 remain text-derived; no new image factual verification.']}
    save(directory/'manifest.json',{'dataset_sha256':report['dataset_sha256'],
        'sampling_plan_sha256':report['sampling_plan_sha256'],'source_seed_bank_sha256':source_sha,
        'config_sha256':report['config_sha256'],'records':len(records),'shards':shards})
    save(ROOT/config['report_path'],report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
