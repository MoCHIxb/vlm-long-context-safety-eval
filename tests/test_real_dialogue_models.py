import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_real_dialogue_supplement import sources, FakeAdapter
from longvision_eval.real_dialogue_supplement import derive_records


class OtherModelTests(unittest.TestCase):
    def setUp(self):
        project=Path(__file__).resolve().parents[1]
        temp=tempfile.TemporaryDirectory(dir=project/'outputs')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.output=self.root/'run'
        self.output.mkdir()
        self.records,_=derive_records(sources())
        spec=importlib.util.spec_from_file_location('other_models_cli',project/'scripts/run_real_dialogue_models.py')
        self.cli=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def invoke(self,model,extra,adapter):
        config=dict(model_key=model,generation=dict(max_new_tokens=1024,do_sample=False,repetition_penalty=1.05))
        (self.output/'manifest.json').write_text(json.dumps(dict(protocol=config)))
        prepared=(config,dict(key=model),self.records,self.records[:1],self.output,'fp')
        args=['models','--model',model,'--site','synthetic']+extra
        with patch.object(self.cli,'ROOT',self.root),patch.object(self.cli,'prepare',return_value=prepared),patch.object(self.cli.sys,'argv',args),patch('sys.stdout',new_callable=io.StringIO),patch('longvision_eval.models.create_adapter',return_value=adapter) as factory:
            result=self.cli.main()
        return result,factory

    def test_explicit_model_required_and_qwen_not_redirected(self):
        for args in [[],['--model','qwen3vl8b','--site','s']]:
            with patch.object(self.cli.sys,'argv',['models']+args),patch('sys.stderr',new_callable=io.StringIO):
                with self.assertRaises(SystemExit):self.cli.main()

    def test_plan_has_no_gpu_load(self):
        result,factory=self.invoke('llava7b',[],FakeAdapter())
        self.assertEqual(result,0)
        factory.assert_not_called()

    def test_llava_gate_exports_correct_model_actual_feedback_and_resumes(self):
        adapter=FakeAdapter()
        result,_=self.invoke('llava7b',['--stage','gate','--execute'],adapter)
        self.assertEqual(result,0)
        self.assertEqual(len(adapter.calls),20)
        self.assertEqual(adapter.calls[1][1]['content'],'ACTUAL_1')
        export=json.loads(next((self.output/'trajectories').glob('*.json')).read_text())
        self.assertEqual(export['model_key'],'llava7b')
        result,factory=self.invoke('llava7b',['--stage','gate','--execute'],FakeAdapter())
        self.assertEqual(result,0)
        factory.assert_not_called()

    def test_gemma_all_does_not_duplicate_gate(self):
        adapter=FakeAdapter()
        result,_=self.invoke('gemma3_12b',['--stage','all','--execute'],adapter)
        self.assertEqual(result,0)
        self.assertEqual(len(adapter.calls),len(self.records)*20)
        export=json.loads(next((self.output/'trajectories').glob('*.json')).read_text())
        self.assertEqual(export['model_key'],'gemma3_12b')

    def test_empty_gate_stops_before_other_stages_and_retains_attempt(self):
        result,_=self.invoke('llava7b',['--stage','all','--execute'],FakeAdapter(empty=True))
        self.assertEqual(result,2)
        self.assertFalse((self.output/'primary').exists())
        error=json.loads(next((self.output/'calibration/errors').glob('*.json')).read_text())
        self.assertEqual(error['last_attempt']['response']['output_tokens'],1)
        self.assertEqual(error['last_attempt']['response']['text'],'')
        result,factory=self.invoke('llava7b',['--stage','all','--execute'],FakeAdapter())
        self.assertEqual(result,2)
        factory.assert_not_called()
