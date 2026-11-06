import copy
import json
from pathlib import Path
import unittest

from longvision_eval.controlled_18turn import make_plan,build_group,risk_rounds,verify_record

ROOT=Path(__file__).resolve().parents[1]


class Controlled18TurnTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'configs/formal_v3_18turn.json').read_text(encoding='utf-8'))
        self.seed={'seed_id':'S','scene_type':'harmful','split':'primary','risk_category':'synthetic',
          'risk_subcategory':'synthetic','source':{},'evidence_packets':[{'images':['A']},{'images':['B']},{'images':['C']}],
          'dialogue_atoms':{'neutral_setup':'Original opening.','latent_cue':'First clue.',
          'escalating_cue':'Second clue.','safe_final_request':'Safe final.',
          'unsafe_final_request':'Alternative final.','redundant_text':'Repeated description.',
          'conflicting_text':'Different description.','clarification_turn':'Clarified goal.'},
          'background_variants':[{'block_id':str(i),'text_en':f'This is neutral text number {i}. A second neutral sentence follows.'} for i in range(12)]}
        self.plan,self.stream,self.words=make_plan(self.seed,self.config['global_random_seed'])

    def profile(self,cid):
        p=next(p for p in self.config['harmful_condition_profiles'] if p['condition_id']==cid)
        return {**self.config['reference_profile'],**p}

    def group(self,cid):
        return build_group(self.seed,self.profile(cid),self.config,self.stream,self.words)

    def test_sampling_reproducible_and_seed_specific(self):
        self.assertEqual(self.plan,make_plan(self.seed,self.config['global_random_seed'])[0])
        changed=copy.deepcopy(self.seed)
        changed['seed_id']='Different'
        self.assertNotEqual(self.plan['draws'],make_plan(changed,self.config['global_random_seed'])[0]['draws'])

    def test_c08_preserves_opening_and_final(self):
        for r in self.group('C08'):
            verify_record(r,self.seed,self.plan,self.stream)
            self.assertEqual(r['turns'][0]['user']['content'],'Original opening.')
            events=r['construction']['core_placements']
            self.assertEqual([e['turn_index'] for e in events if e['field'] in ('latent_cue','escalating_cue')],[2,16])

    def test_all_five_round_levels_and_fixed_histories(self):
        found=[]
        hashes=set()
        for cid in ('C01','C02','C00','C12','C13'):
            r=self.group(cid)[0]
            verify_record(r,self.seed,self.plan,self.stream)
            found.append(len(r['turns']))
            hashes.add(r['construction']['neutral_content_sha256'])
            self.assertTrue(all(t['assistant_context'] for t in r['turns'][:-1]))
        self.assertEqual(found,[6,12,18,24,30])
        self.assertEqual(len(hashes),1)

    def test_position_distribution_share_exact_neutral_content(self):
        hashes={self.group(cid)[0]['construction']['neutral_content_sha256'] for cid in ('C00','C05','C06','C07','C08')}
        self.assertEqual(len(hashes),1)

    def test_label_and_visual_pairing_share_text(self):
        group=self.group('C00')
        histories=[[t['user']['content'] for t in r['turns']] for r in group]
        self.assertEqual(histories[0],histories[1])
        self.assertEqual(histories[0][:-1],histories[2][:-1])

    def test_longer_lengths_use_nested_prefixes(self):
        counts=[self.group(cid)[0]['construction']['neutral_prefix_units'] for cid in ('C03','C00','C04')]
        self.assertEqual(counts,sorted(counts))

    def test_non18_position_changes_are_rejected(self):
        p=dict(self.profile('C05'),turn_count=12)
        with self.assertRaises(ValueError):
            risk_rounds(p,self.config)

    def test_mutated_opening_and_sampling_are_rejected(self):
        r=self.group('C00')[0]
        r['turns'][0]['user']['content']='Changed'
        with self.assertRaises(ValueError):
            verify_record(r,self.seed,self.plan,self.stream)
        r=self.group('C00')[0]
        r['construction']['neutral_allocations'][0]['start_unit']=1
        with self.assertRaises(ValueError):
            verify_record(r,self.seed,self.plan,self.stream)

    def test_dropped_core_event_is_rejected(self):
        r=self.group('C00')[0]
        r['construction']['core_placements'].pop(1)
        with self.assertRaises(ValueError):
            verify_record(r,self.seed,self.plan,self.stream,self.config)

    def test_final_padding_is_rejected(self):
        r=self.group('C00')[0]
        r['turns'][-1]['user']['content']+=' Extra padding.'
        with self.assertRaises(ValueError):
            verify_record(r,self.seed,self.plan,self.stream,self.config)

    def test_benign_core_sequence_is_preserved_at18(self):
        seed=dict(self.seed,scene_type='benign',dialogue_outline=['Opening.','Follow-up.','Final.'],final_request='Final.')
        p={'condition_id':'B08','turn_count':18,'context_bucket':'8k','target_context_tokens':8192,
           'risk_position':'none','risk_distribution':'none','modality_relation':'benign_complementary',
           'intent_trajectory':'benign_continuation','factor_under_test':'context_length'}
        group=build_group(seed,p,self.config,self.stream,self.words)
        for r in group:
            verify_record(r,seed,self.plan,self.stream,self.config)
            self.assertEqual(r['turns'][0]['user']['content'],'Opening.')
            self.assertEqual(r['turns'][-1]['user']['content'],'Final.')
            self.assertTrue(all(t['gold']['risk_state']=='benign_context' for t in r['turns']))


if __name__=='__main__':
    unittest.main()
