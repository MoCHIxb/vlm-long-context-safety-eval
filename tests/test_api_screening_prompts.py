import copy
import json
from pathlib import Path
import unittest

from longvision_eval.annotation import OUTCOMES

ROOT = Path(__file__).resolve().parents[1]


class APIScreeningPromptTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'configs/evaluation/formal_v3_api_screening_v1.json').read_text(encoding='utf-8'))
        self.schema = json.loads((ROOT / self.config['output_schema']).read_text(encoding='utf-8'))
        self.example = json.loads((ROOT / 'prompts/evaluation/formal_v3_screening_example_output.json').read_text(encoding='utf-8'))

    def validator(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest('Optional JSON-schema validation dependency is not installed')
        Draft202012Validator.check_schema(self.schema)
        return Draft202012Validator(self.schema)

    def test_package_is_offline_blinded_and_reuses_outcome_vocabulary(self):
        self.assertFalse(self.config['execute_enabled'])
        self.assertIsNone(self.config['model'])
        for field in ('system_prompt', 'user_template', 'output_schema'):
            self.assertTrue((ROOT / self.config[field]).is_file())
        self.assertIn('{{CANDIDATE_JSON}}', (ROOT / self.config['user_template']).read_text(encoding='utf-8'))
        self.assertEqual(set(self.schema['properties']['outcome']['enum']), OUTCOMES)
        for field in ('model_id', 'seed_id', 'label', 'gold', 'condition_id', 'expected_behavior'):
            self.assertIn(field, self.config['blind_fields'])

    def test_example_and_evidence_offsets_are_valid(self):
        self.validator().validate(self.example)
        source = json.loads((ROOT / 'prompts/evaluation/formal_v3_screening_example_input.json').read_text(encoding='utf-8'))
        self.assertEqual(source['candidate_id'], self.example['candidate_id'])
        text = source['target_response']['text']
        for span in self.example['evidence_spans']:
            self.assertTrue(0 <= span['start'] < span['end'] <= len(text))
        span = self.example['evidence_spans'][0]
        self.assertEqual(text[span['start']:span['end']], 'Never share your login code.')

    def test_conflicting_labels_and_unreviewed_uncertainty_are_rejected(self):
        validator = self.validator()
        cases = []
        value = copy.deepcopy(self.example)
        value['safety_label'] = 'unsafe'
        cases.append(value)
        value = copy.deepcopy(self.example)
        value.update(safety_label='unclear', outcome='unclear')
        cases.append(value)
        value = copy.deepcopy(self.example)
        value['technical_flags'] = ['generation_error']
        cases.append(value)
        value = copy.deepcopy(self.example)
        value['model_name'] = 'must-not-leak'
        cases.append(value)
        for value in cases:
            with self.subTest(value=value):
                self.assertTrue(list(validator.iter_errors(value)))

    def test_truncation_is_not_automatically_unsafe_or_unclear(self):
        value = copy.deepcopy(self.example)
        value['technical_flags'] = ['output_truncated']
        value['truncation_affects_judgment'] = False
        self.validator().validate(value)

    def test_safe_but_irrelevant_answer_is_distinct_from_helpful(self):
        value = copy.deepcopy(self.example)
        value.update(outcome='unclear', task_fulfillment='not_fulfilled',
                     requires_human_review=True, review_reasons=['unclear_judgment'])
        self.validator().validate(value)


if __name__ == '__main__':
    unittest.main()
