import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from longvision_eval.models.base import GenerationResult
from longvision_eval.free_history_supplement import run_trajectory
from longvision_eval.real_dialogue_supplement import derive_records, choose_gate, write_gzip_jsonl, read_bundle, export_trajectory


def sources():
    rows=[]
    for track in ('harmful_controlled','benign_controlled'):
        for schedule in ('static_initial_bundle','dynamic_incremental'):
            for label in (('safe','unsafe') if track=='harmful_controlled' else ('safe',)):
                condition='C00' if track=='harmful_controlled' else 'B08'
                sid=f'{track}-{schedule}-{label}'
                rows.append(dict(sample_id=sid,seed_id=track,split='calibration',pair_id=f'{track}-{schedule}',
                    condition_id=condition,track=track,label=label,
                    variables=dict(visual_evidence_schedule=schedule,context_bucket='8k',turn_count=18),
                    turns=[dict(turn_index=t,user=dict(content=f'neutral task {t}' if t<18 else f'neutral goal {label}',images=[]),
                        assistant_context='REFERENCE_SENTINEL',gold=dict(marker='GOLD_SENTINEL')) for t in range(1,19)]))
    return rows


class FakeAdapter:
    def __init__(self,fail_at=None,empty=False):
        self.calls=[]
        self.fail_at=fail_at
        self.empty=empty

    def generate(self,messages,generation):
        self.calls.append(copy.deepcopy(messages))
        if len(self.calls)==self.fail_at:
            raise RuntimeError('synthetic interruption')
        return GenerationResult(text='' if self.empty else f'ACTUAL_{len(self.calls)}',input_tokens=99,
            output_tokens=1 if self.empty else 3,truncated=False)

    def runtime_info(self):
        return dict(adapter='synthetic-no-GPU')


class RealDialogueTests(unittest.TestCase):
    def setUp(self):
        project=Path(__file__).resolve().parents[1]
        (project/'outputs').mkdir(exist_ok=True)
        temp=tempfile.TemporaryDirectory(dir=project/'outputs')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.output=self.root/'run'
        self.output.mkdir()
        self.records,self.annotations=derive_records(sources())
        self.record=self.records[0]
        self.generation=dict(max_new_tokens=1024,do_sample=False,repetition_penalty=1.05)

    def test_preserves_original_users_strips_reference_and_gold(self):
        original={r['sample_id']:r for r in sources()}
        for r in self.records:
            self.assertEqual([t['user'] for t in r['turns'][:18]], [t['user'] for t in original[r['source_sample_id']]['turns']])
            self.assertEqual(len(r['turns']),20)
        self.assertNotIn('REFERENCE_SENTINEL',json.dumps(self.records))
        self.assertNotIn('GOLD_SENTINEL',json.dumps(self.records))
        self.assertIn('GOLD_SENTINEL',json.dumps(self.annotations))

    def test_followups_reuse_existing_goals_and_only_unsafe_group_switches(self):
        for r in self.records:
            self.assertEqual(r['turns'][18]['user'],r['turns'][17]['user'])
            self.assertEqual(r['turns'][19]['user']['content'],'neutral goal safe')
            self.assertEqual(r['followup_origins'][1]['source_turn_index'],18)

    def test_pair_leakage_and_missing_pair_rejected(self):
        raw=sources()
        raw[1]['split']='heldout'
        with self.assertRaises(ValueError): derive_records(raw)
        raw=sources()
        raw[1]['turns'][4]['user']['content']='changed shared prefix'
        with self.assertRaises(ValueError): derive_records(raw)
        with self.assertRaises(ValueError): derive_records(sources()[1:])

    def test_gate_is_unique_and_from_calibration(self):
        gate=choose_gate(self.records)
        self.assertEqual(len({r['sample_id'] for r in gate}),4)
        self.assertTrue(all(r['split']=='calibration' for r in gate))
        self.assertEqual({r['track'] for r in gate},{'harmful_controlled','benign_controlled'})

    def test_bundle_roundtrip_and_reproducible_bytes(self):
        a,b=self.root/'a.gz',self.root/'b.gz'
        write_gzip_jsonl(a,self.records)
        write_gzip_jsonl(b,self.records)
        self.assertEqual(a.read_bytes(),b.read_bytes())
        self.assertEqual(read_bundle(a),self.records)

    def test_complete_transcript_actual_feedback_and_annotation_work_preserved(self):
        adapter=FakeAdapter()
        result=run_trajectory(self.record,adapter,self.generation,self.root,self.output,'fp')
        transcript=export_trajectory(self.root,self.record,result,self.output,'fp')
        self.assertEqual(adapter.calls[1][1]['content'],'ACTUAL_1')
        self.assertNotIn('GOLD_SENTINEL',json.dumps(adapter.calls))
        self.assertEqual(transcript['turns'][0]['user'],self.record['turns'][0]['user'])
        self.assertEqual(transcript['turns'][0]['response']['text'],'ACTUAL_1')
        path=self.output/'assessment_to_fill'/(self.record['sample_id']+'.json')
        draft=json.loads(path.read_text())
        self.assertIsNone(draft['turns'][0]['harmful_output'])
        draft['status']='reviewer_work_in_progress'
        path.write_text(json.dumps(draft))
        export_trajectory(self.root,self.record,result,self.output,'fp')
        self.assertEqual(json.loads(path.read_text())['status'],'reviewer_work_in_progress')

    def test_interruption_resumes_and_changed_exports_rejected(self):
        with self.assertRaises(RuntimeError):
            run_trajectory(self.record,FakeAdapter(fail_at=3),self.generation,self.root,self.output,'fp')
        adapter=FakeAdapter()
        result=run_trajectory(self.record,adapter,self.generation,self.root,self.output,'fp')
        self.assertEqual(len(adapter.calls),18)
        export_trajectory(self.root,self.record,result,self.output,'fp')
        path=self.output/'trajectories'/(self.record['sample_id']+'.json')
        path.write_text('{}')
        with self.assertRaises(ValueError): export_trajectory(self.root,self.record,result,self.output,'fp')

    def cli(self):
        path=Path(__file__).resolve().parents[1]/'scripts/run_real_dialogue_supplement.py'
        spec=importlib.util.spec_from_file_location('rd_cli_test',path)
        cli=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        return cli

    def test_plan_does_not_create_adapter(self):
        cli=self.cli()
        prepared=(dict(generation=self.generation),{},self.records,self.records[:1],self.output,'fp')
        with patch.object(cli,'ROOT',self.root),patch.object(cli,'prepare',return_value=prepared),patch.object(cli.sys,'argv',['rd','--site','test']),patch('sys.stdout',new_callable=io.StringIO),patch('longvision_eval.models.create_adapter') as factory:
            self.assertEqual(cli.main(),0)
            factory.assert_not_called()

    def test_gate_failure_stops_primary_records_empty_attempt_and_explicit_retry(self):
        cli=self.cli()
        gate=[self.record]
        primary=copy.deepcopy(self.records[-1]);primary.update(sample_id='primary-test',split='primary')
        prepared=(dict(generation=self.generation),{},[self.record,primary],gate,self.output,'fp')
        args=['rd','--site','test','--stage','primary','--execute']
        with patch.object(cli,'ROOT',self.root),patch.object(cli,'prepare',return_value=prepared),patch('sys.stdout',new_callable=io.StringIO):
            with patch.object(cli.sys,'argv',args),patch('longvision_eval.models.create_adapter',return_value=FakeAdapter(empty=True)):
                self.assertEqual(cli.main(),2)
            self.assertFalse((self.output/'primary').exists())
            error=json.loads(next((self.output/'calibration/errors').glob('*.json')).read_text())
            self.assertEqual(error['last_attempt']['turn_index'],1)
            self.assertEqual(error['last_attempt']['response']['text'],'')
            self.assertEqual(error['last_attempt']['response']['output_tokens'],1)
            with patch.object(cli.sys,'argv',args),patch('longvision_eval.models.create_adapter') as factory:
                self.assertEqual(cli.main(),2)
                factory.assert_not_called()
            adapter=FakeAdapter()
            with patch.object(cli.sys,'argv',args+['--retry-errors']),patch('longvision_eval.models.create_adapter',return_value=adapter):
                self.assertEqual(cli.main(),0)
            self.assertEqual(len(adapter.calls),40)
            with patch.object(cli.sys,'argv',args),patch('longvision_eval.models.create_adapter') as factory:
                self.assertEqual(cli.main(),0)
                factory.assert_not_called()

    def test_gate_results_are_reused_by_full_calibration(self):
        cli=self.cli()
        prepared=(dict(generation=self.generation),{},self.records,self.records[:1],self.output,'fp')
        adapter=FakeAdapter()
        with patch.object(cli,'ROOT',self.root),patch.object(cli,'prepare',return_value=prepared),patch.object(cli.sys,'argv',['rd','--site','test','--stage','all','--execute']),patch('sys.stdout',new_callable=io.StringIO),patch('longvision_eval.models.create_adapter',return_value=adapter):
            self.assertEqual(cli.main(),0)
        self.assertEqual(len(adapter.calls),len(self.records)*20)
