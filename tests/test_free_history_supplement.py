import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from longvision_eval.models.base import GenerationResult
from longvision_eval.free_history_supplement import run_trajectory, summarize, RunLock


class FakeAdapter:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def generate(self, messages, generation):
        self.calls.append((copy.deepcopy(messages), dict(generation)))
        if len(self.calls) == self.fail_at:
            raise RuntimeError('synthetic interruption')
        return GenerationResult(text='REAL_REPLY_' + str(len(self.calls)), input_tokens=100,
                                output_tokens=3, truncated=False, duration_seconds=0.5, peak_gpu_memory_mb=8)

    def runtime_info(self):
        return {'adapter': 'fake', 'gpu': 'none'}


class FreeHistoryTests(unittest.TestCase):
    def setUp(self):
        workspace_output = Path(__file__).resolve().parents[1] / 'outputs'
        workspace_output.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=workspace_output)
        Path(self.temp.name).resolve().relative_to(workspace_output.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'results'
        self.output.mkdir()
        self.record = {'sample_id': 'sample-1', 'seed_id': 'seed-1', 'turns': [
            {'turn_index': i, 'user': {'content': 'USER_' + str(i), 'images': []},
             'assistant_context': 'REFERENCE_MUST_NOT_APPEAR'} for i in [1, 2, 3]]}
        self.generation = {'max_new_tokens': 1024, 'do_sample': False, 'repetition_penalty': 1.05}

    def run_case(self, adapter, record=None):
        return run_trajectory(record or self.record, adapter, self.generation, self.root, self.output, 'fp')

    def test_all_turns_generated_and_actual_answers_are_carried_forward(self):
        adapter = FakeAdapter()
        result = self.run_case(adapter)
        self.assertEqual(len(adapter.calls), 3)
        self.assertEqual(adapter.calls[1][0][1], {'role': 'assistant', 'content': 'REAL_REPLY_1'})
        self.assertEqual(adapter.calls[2][0][3]['content'], 'REAL_REPLY_2')
        self.assertTrue(all(options == self.generation for _, options in adapter.calls))
        self.assertNotIn('REFERENCE_MUST_NOT_APPEAR', json.dumps(adapter.calls))
        self.assertTrue(all(t['response']['source'] == 'model' for t in result['turns']))

    def test_interruption_resumes_last_committed_turn_and_completed_results_are_skipped(self):
        with self.assertRaises(RuntimeError):
            self.run_case(FakeAdapter(fail_at=2))
        checkpoint = json.loads((self.output / 'checkpoints/sample-1.json').read_text())
        self.assertEqual(len(checkpoint['turns']), 1)
        resumed = FakeAdapter()
        result = self.run_case(resumed)
        self.assertEqual(len(resumed.calls), 2)
        self.assertEqual(resumed.calls[0][0][1]['content'], 'REAL_REPLY_1')
        self.assertEqual(result['turns'][0]['response']['text'], 'REAL_REPLY_1')
        never = FakeAdapter(fail_at=1)
        self.run_case(never)
        self.assertEqual(never.calls, [])

    def test_checkpoint_edit_is_rejected_before_generation(self):
        with self.assertRaises(RuntimeError):
            self.run_case(FakeAdapter(fail_at=2))
        path = self.output / 'checkpoints/sample-1.json'
        value = json.loads(path.read_text())
        value['turns'][0]['response']['text'] = 'MODIFIED'
        path.write_text(json.dumps(value))
        adapter = FakeAdapter()
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.run_case(adapter)
        self.assertFalse(adapter.calls)

    def test_changed_input_or_model_identity_cannot_resume(self):
        self.run_case(FakeAdapter())
        changed = copy.deepcopy(self.record)
        changed['turns'][0]['user']['content'] = 'DIFFERENT'
        with self.assertRaisesRegex(ValueError, 'source or run'):
            self.run_case(FakeAdapter(), changed)
        with self.assertRaisesRegex(ValueError, 'source or run'):
            run_trajectory(self.record, FakeAdapter(), self.generation, self.root, self.output, 'different-model')

    def test_technical_summary_counts_calls_once_with_retained_checkpoint(self):
        self.run_case(FakeAdapter())
        stats = summarize(self.output, [self.record], 'fp', self.root)
        self.assertEqual(stats['committed_model_calls'], 3)
        self.assertEqual(stats['total_generation_seconds'], 1.5)
        self.assertTrue(stats['complete'])
        self.assertEqual(stats['planned'], 1)

    def test_empty_generation_is_not_committed_as_safe_or_valid(self):
        class Empty(FakeAdapter):
            def generate(self, messages, generation):
                return GenerationResult(text='')
        with self.assertRaisesRegex(ValueError, 'Empty'):
            self.run_case(Empty())
        self.assertFalse((self.output / 'sample-1.json').exists())

    def test_goal_pair_prefix_audit_excludes_the_different_final_request(self):
        class Stable(FakeAdapter):
            def generate(self, messages, generation):
                return GenerationResult(text='reply-to-' + messages[-1]['content'][-1]['text'])
        pair = []
        for label in ['safe', 'unsafe']:
            record = copy.deepcopy(self.record)
            record.update(sample_id='sample-' + label, label=label, condition_id='C00',
                          variables={'visual_evidence_schedule': 'static_initial_bundle'})
            record['turns'][-1]['user']['content'] = 'final-goal-' + label
            self.run_case(Stable(), record)
            pair.append(record)
        stats = summarize(self.output, pair, 'fp', self.root)
        self.assertEqual(stats['goal_pairs_completed'], 1)
        self.assertEqual(stats['goal_pairs_with_identical_generated_prefix'], 1)

    def test_truncated_actual_text_is_preserved_and_flagged(self):
        class Truncated(FakeAdapter):
            def generate(self, messages, generation):
                result = super().generate(messages, generation)
                result.truncated = True
                return result
        adapter = Truncated()
        self.run_case(adapter)
        stats = summarize(self.output, [self.record], 'fp', self.root)
        self.assertEqual(stats['truncated_history_calls'], 2)
        self.assertEqual(stats['truncated_final_calls'], 1)
        self.assertEqual(adapter.calls[1][0][1]['content'], 'REAL_REPLY_1')

    def test_os_lock_prevents_duplicate_and_releases(self):
        path = self.root / 'lock'
        with RunLock(path):
            with self.assertRaises(RuntimeError):
                with RunLock(path):
                    pass
        with RunLock(path):
            pass

    def test_cli_gate_failure_stops_formal_and_explicit_retry_resumes(self):
        source = Path(__file__).resolve().parents[1] / 'scripts/run_free_history_supplement.py'
        spec = importlib.util.spec_from_file_location('free_history_cli_test', source)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        gate_record = copy.deepcopy(self.record)
        gate_record['sample_id'] = 'gate-only'
        protocol = {'generation': self.generation, 'history_mode': 'model_generated_every_turn'}
        prepared = (protocol, {}, [self.record], [gate_record], self.output, 'fp')
        args = ['probe', '--model', 'qwen25vl7b', '--site', 'fake', '--execute']
        with patch.object(cli, 'ROOT', self.root), patch.object(cli, 'prepare', return_value=prepared), patch('sys.stdout', new_callable=io.StringIO):
            with patch.object(cli.sys, 'argv', args), patch('longvision_eval.models.create_adapter', return_value=FakeAdapter(fail_at=2)):
                self.assertEqual(cli.main(), 2)
            self.assertFalse((self.output / 'formal').exists())
            with patch.object(cli.sys, 'argv', args), patch('longvision_eval.models.create_adapter') as factory:
                self.assertEqual(cli.main(), 2)
                factory.assert_not_called()
            with patch.object(cli.sys, 'argv', args + ['--retry-errors']), patch('longvision_eval.models.create_adapter', return_value=FakeAdapter()):
                self.assertEqual(cli.main(), 0)
            progress = json.loads((self.output / 'progress.json').read_text())
            self.assertEqual(progress['status'], 'complete')
            self.assertEqual(progress['completed_trajectories'], 1)
            self.assertTrue((self.output / 'formal/sample-1.json').exists())


if __name__ == '__main__':
    unittest.main()
