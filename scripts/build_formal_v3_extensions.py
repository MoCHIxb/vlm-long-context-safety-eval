#!/usr/bin/env python3
"""Build controlled trajectories using accepted original cores and API synonyms."""
import copy
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import gzip
from collections import Counter, defaultdict

import build_formal_v3 as base
from validate_formal_v3 import aggregate_images, text_history, validate_seed_bank

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+',text.strip()) if s.strip()]


def filler_sentences(variants, word_budget):
    sentences = [s for block in variants for s in split_sentences(block)]
    if not sentences:
        raise ValueError('No neutral paraphrase sentences')
    chosen, words, cursor = [], 0, 0
    while words < word_budget:
        sentence = sentences[cursor % len(sentences)]
        size = len(sentence.split())
        if words + size > word_budget:
            break
        chosen.append(sentence)
        words += size
        cursor += 1
    return chosen, words, math.ceil(cursor/len(sentences))


def shorten_optional_history(records):
    # A seed's reference history is shortened once for all its length variants.
    shortest = min(r['variables']['target_context_tokens'] for r in records)
    representative = records[0]['turns']
    user_max = max(sum(len(t['user']['content'].split()) for t in r['turns']) for r in records)
    available = max(0,round(shortest*0.75)-user_max-50)
    contexts = [t.get('assistant_context') or '' for t in representative[:-1]]
    total = sum(len(x.split()) for x in contexts)
    if total <= available:
        return 0
    kept = []
    for text in contexts:
        allowance = int(available*len(text.split())/max(1,total))
        selected, used = [], 0
        for sentence in split_sentences(text):
            count = len(sentence.split())
            if used+count > allowance:
                break
            selected.append(sentence)
            used += count
        kept.append(' '.join(selected))
    for record in records:
        if len(record['turns']) != len(representative):
            raise ValueError('Reference history turn count mismatch')
        for turn,text in zip(record['turns'][:-1],kept):
            turn['assistant_context'] = text
    return total-sum(len(t.split()) for t in kept)


def fill_group(records, variants):
    target = records[0]['variables']['target_context_tokens']
    average_words = sum(base.estimate(r['turns'])[0] for r in records)/len(records)
    sentences, words, cycles = filler_sentences(variants,max(0,round(target*0.75-average_words)))
    slots = len(records[0]['turns'])-1
    pieces = [[] for _ in range(slots)]
    quota = math.ceil(words/max(1,slots))
    slot = used = 0
    for sentence in sentences:
        if used >= quota and slot < slots-1:
            slot += 1
            used = 0
        pieces[slot].append(sentence)
        used += len(sentence.split())
    for record in records:
        for turn,piece in zip(record['turns'][:-1],pieces):
            turn['assistant_context'] = '\n\n'.join(x for x in [turn.get('assistant_context') or '', ' '.join(piece)] if x)
        count,tokens = base.estimate(record['turns'])
        record['context_stats'] = {'whitespace_words':count,'estimated_tokens':tokens,
            'estimator':'whitespace_words_divided_by_0.75','neutral_fill_words':words,
            'neutral_sentence_count':len(sentences),'neutral_variant_cycles':cycles,
            'actual_model_input_tokens_measured':False}
        record['construction'].update(background_method='fixed_order_neutral_synonymous_sentence_cycle',
            background_source='API paraphrases of the original neutral setup',
            final_request_padding=False,core_acceptance='data/seeds/formal_v3_core_acceptance.json')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--embedded',action='store_true',help='Rebuild from the released seed bank without API logs')
    args=parser.parse_args()
    status_path = ROOT/'outputs/formal_v3_original_core_extensions/pipeline_status.json'
    released_bank=ROOT/'data/seeds/formal_v3_extended_seed_bank.json'
    embedded=args.embedded or not status_path.exists()
    status = load(status_path) if status_path.exists() else {
        'status':'extensions_integrated_original_core_accepted','background_run':None,'condition_run':None}
    if embedded:
        status.update(status='extensions_integrated_original_core_accepted',revised_bank=str(released_bank))
    if status.get('status') not in {'candidate_generation_complete_pending_human_review','extensions_integrated_original_core_accepted'}:
        raise ValueError('Complete all API generation stages first')
    original = ROOT/'data/seeds/formal_v3_seed_bank.json'
    accepted = load(ROOT/'data/seeds/formal_v3_core_acceptance.json')
    if hashlib.sha256(original.read_bytes()).hexdigest() != accepted['original_seed_bank_sha256']:
        raise ValueError('Accepted core hash changed')
    bank = load(Path(status['revised_bank']))
    original_bank = load(original)
    prior_flagged = ('V3H-DE-11','V3H-DE-13','V3H-DE-16','V3H-CY-11','V3H-PS-07','V3H-PS-13')
    accepted.update(prior_flagged_seed_ids=list(prior_flagged),
                    resolution='User accepted the original wording of all 144 seeds; earlier flags retained for traceability')
    write(ROOT/'data/seeds/formal_v3_core_acceptance.json',accepted)
    originals = {s['seed_id']:s for s in original_bank['harmful']+original_bank['benign']}
    background = Path(status['background_run']) if status.get('background_run') else None
    variants = {}
    for seed in bank['harmful']+bank['benign']:
        sid = seed['seed_id']
        core = originals[sid]
        for field in ('neutral_setup','latent_cue','escalating_cue','unsafe_final_request','safe_final_request'):
            if field in core.get('dialogue_atoms',{}) and seed['dialogue_atoms'][field] != core['dialogue_atoms'][field]:
                raise ValueError('Original core wording changed')
        value = ({'blocks':seed['background_variants']} if embedded
                 else load(background/sid/'candidate.json')['candidate'])
        variants[sid] = [b['text_en'] for b in value['blocks']]
        seed['background_variants'] = value['blocks']
        seed['status'] = 'user_accepted_core_with_api_generated_extensions'
        seed['review'] = {'core_decision':'accepted','decision_source':'explicit user instruction',
            'acceptance_record':'data/seeds/formal_v3_core_acceptance.json',
            'independent_double_review_recorded':False,
            'generated_extensions_individually_human_scored':False,
            'integration_authorized_by_user':True}
        if sid in prior_flagged:
            seed['prior_review_flag'] = {'retained_for_traceability':True,
                'resolution':'Original wording retained under explicit user acceptance',
                'sensitivity_analysis_recommended':True}
        existing=seed.get('extension_provenance',{})
        seed['extension_provenance'] = {'background_candidate':existing.get('background_candidate') if embedded else str((background/sid/'candidate.json').relative_to(ROOT)),
            'condition_run':(existing.get('condition_run') if embedded else str(Path(status['condition_run']).relative_to(ROOT))) if seed['scene_type']=='harmful' else None,
            'core_accepted_by_user':True,'generated_extensions_individually_human_scored':False,
            'integration_authorized_by_user':True,'image_facts_verified_by_api':False}
    bank['status'] = 'user_accepted_core_with_api_generated_extensions'
    bank['base_schema_version'] = bank.get('base_schema_version',bank.get('schema_version'))
    bank['schema_version'] = '4.1.0-original-core-extensions'
    validate_seed_bank(bank,load(ROOT/'configs/formal_v3_taxonomy.json'))
    config = load(ROOT/'configs/formal_v3.json')
    config['schema_version'] = '4.1.0-original-core-extensions'
    config['dataset_name'] += '-OriginalCoreExtensions'
    schedules = [s['id'] for s in config['visual_evidence_schedules']]
    base.add_context_filler = lambda *args: None
    base.pad_to_word_count = lambda text,target: text
    records, trimmed = [], {}
    for seed in bank['harmful']:
        for profile in base.merged_profiles(config):
            group = [base.build_harmful_record(seed,profile,schedule,label,config)
                     for schedule in schedules for label in config['harmful_labels']]
            fill_group(group,variants[seed['seed_id']])
            records.extend(group)
    for seed in bank['benign']:
        seed_records = [base.build_benign_record(seed,profile,schedule,config)
                        for profile in config['benign_context_profiles'] for schedule in schedules]
        for record in seed_records:
            record['turns'][-1]['user']['content'] = seed['final_request']
        trimmed[seed['seed_id']] = shorten_optional_history(seed_records)
        for i in range(0,len(seed_records),len(schedules)):
            group = seed_records[i:i+len(schedules)]
            fill_group(group,variants[seed['seed_id']])
            records.extend(group)
    assert len(records)==4224 and len({r['sample_id'] for r in records})==4224
    pairs, visual = defaultdict(list),defaultdict(list)
    deviations = []
    for record in records:
        if record['pair_id']:
            pairs[record['pair_id']].append(record)
        visual[record['schedule_pair_id']].append(record)
        deviations.append(abs(record['context_stats']['estimated_tokens']-record['variables']['target_context_tokens'])/record['variables']['target_context_tokens'])
        assert len(aggregate_images(record))==len(set(aggregate_images(record)))
    for pair in pairs.values():
        assert len(pair)==2 and text_history(pair[0])[:-1]==text_history(pair[1])[:-1]
        assert aggregate_images(pair[0])==aggregate_images(pair[1])
    for pair in visual.values():
        assert len(pair)==2 and text_history(pair[0])==text_history(pair[1])
        assert aggregate_images(pair[0])==aggregate_images(pair[1])
    seed_output = ROOT/'data/seeds/formal_v3_extended_seed_bank.json'
    output = ROOT/'data/processed/formal_v3_extended.jsonl'
    write(seed_output,bank)
    with output.open('w',encoding='utf-8',newline='\n') as handle:
        for record in records:
            handle.write(json.dumps(record,ensure_ascii=False)+'\n')
    summary = {'status':'built_from_user_accepted_original_core_and_api_extensions',
        'trajectory_count':len(records),'independent_seeds':144,'safe_unsafe_pairs':len(pairs),
        'visual_schedule_pairs':len(visual),'condition_segments':240,'background_libraries':144,
        'max_estimated_relative_token_deviation':max(deviations),
        'length_estimator':'whitespace_words_divided_by_0.75',
        'actual_model_input_token_budgets_verified':False,
        'reference_history_shortened_benign_seed_count':sum(v>0 for v in trimmed.values()),
        'source_wording_preserved':True,'core_acceptance':str((ROOT/'data/seeds/formal_v3_core_acceptance.json').relative_to(ROOT)),
        'dataset':str(output.relative_to(ROOT)),'dataset_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'seed_bank':str(seed_output.relative_to(ROOT)),'seed_bank_sha256':hashlib.sha256(seed_output.read_bytes()).hexdigest()}
    shard_dir=ROOT/'data/processed/formal_v3_extended_shards'
    shard_dir.mkdir(parents=True,exist_ok=True)
    groups=defaultdict(list)
    for record in records:
        groups[record['risk_category'] if record['track']=='harmful_controlled' else 'benign'].append(record)
    shards=[]
    for name,items in sorted(groups.items()):
        path=shard_dir/(name+'.jsonl.gz')
        with path.open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed:
                for item in items:
                    compressed.write((json.dumps(item,ensure_ascii=False)+'\n').encode('utf-8'))
        shards.append({'path':str(path.relative_to(ROOT)),'records':len(items),
                       'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    write(shard_dir/'manifest.json',{'dataset_sha256':summary['dataset_sha256'],
        'seed_bank_sha256':summary['seed_bank_sha256'],'records':len(records),'shards':shards})
    config.update(dataset_path=str(output.relative_to(ROOT)),seed_bank_path=str(seed_output.relative_to(ROOT)),
                  status='user_accepted_original_core_with_api_generated_extensions',
                  length_control_basis='whitespace_words_divided_by_0.75',
                  actual_model_input_budgets_verified=False,
                  visual_relation_evidence='existing source text; no new image inspection by API')
    write(ROOT/'configs/formal_v3_extended.json',config)
    summary['shard_manifest']=str((shard_dir/'manifest.json').relative_to(ROOT))
    write(ROOT/'documentation/reports/formal_v3_extensions_status.json',summary)
    status.update(status='extensions_integrated_original_core_accepted',stage=None,
                  six_rewrites_applied=False,
                  core_review_status='144 original seeds explicitly accepted by user',
                  generated_extension_status='API generated and structurally validated; no individual human scores fabricated',
                  integrated_dataset=str(output.relative_to(ROOT)),
                  integrated_seed_bank=str(seed_output.relative_to(ROOT)),
                  trajectories_rebuilt=True)
    status.pop('human_approval',None)
    if status.get('repair_run')=='None':
        status['repair_run']=None
    write(status_path,status)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
