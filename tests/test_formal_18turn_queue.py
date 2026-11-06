import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from longvision_eval.provenance import run_provenance
from longvision_eval.runner import execute

ROOT=Path(__file__).resolve().parents[1]


class FormalQueueTests(unittest.TestCase):
    def test_all_models_share_panel_and_generation(self):
        queues=list((ROOT/'configs/runs/formal_v3_18turn').glob('queue-*.json'))
        self.assertTrue(queues)
        queue=json.loads(queues[-1].read_text(encoding='utf-8'))
        runs=[json.loads((ROOT/m['formal']).read_text(encoding='utf-8')) for m in queue['models']]
        self.assertEqual(len(runs),4)
        self.assertEqual(len({r['expected_dataset_sha256'] for r in runs}),1)
        self.assertEqual(len({json.dumps(r['generation'],sort_keys=True) for r in runs}),1)
        self.assertTrue(all(r['history_mode']=='fixed_reference' and r['stop_on_error'] for r in runs))

    def test_code_version_mismatch_blocks_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'data').write_text('example',encoding='utf-8')
            (root/'code.py').write_text('changed',encoding='utf-8')
            with self.assertRaises(ValueError):
                run_provenance({'dataset_path':'data','expected_code_sha256':{'code.py':'wrong'}},{},root)

    def test_first_error_stops_remaining_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            run={'run_id':'test','output_dir':'outputs','stop_on_error':True}
            model={'model_id':'test','model_name':'test'}
            rows=[{'sample_id':str(i),'turns':[]} for i in range(3)]
            with patch('longvision_eval.runner.load_run',return_value=(run,model,rows)),\
                 patch('longvision_eval.runner.run_provenance',return_value={}),\
                 patch('longvision_eval.runner.create_adapter',return_value=object()),\
                 patch('longvision_eval.runner.run_record',side_effect=RuntimeError('synthetic failure')) as generate,\
                 contextlib.redirect_stderr(io.StringIO()):
                summary=execute(root/'config',root,resume=True)
            self.assertEqual(generate.call_count,1)
            self.assertEqual(summary['failed_now'],1)
            self.assertEqual(summary['pending_samples'],3)
            self.assertTrue(summary['stopped_on_error'])
