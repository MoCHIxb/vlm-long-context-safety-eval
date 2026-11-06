import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_formal_v3_extensions import parse


def response(value, finish='stop'):
    import json
    return {'choices':[{'finish_reason':finish,'message':{'content':json.dumps(value)}}]}


class TextRevisionTests(unittest.TestCase):
    def test_truncated_output_never_becomes_candidate(self):
        with self.assertRaises(ValueError):
            parse(response({'seed_id':'S'},'length'),'conditions','S')

    def test_background_requires_unique_blocks(self):
        v = {'seed_id':'S','blocks':[{'block_id':str(i),'text_en':'Repeated'} for i in range(12)]}
        with self.assertRaises(ValueError):
            parse(response(v),'background','S')

    def test_text_conditions_require_grounding(self):
        with self.assertRaises(ValueError):
            parse(response({'seed_id':'S','evidence_basis':'image_verified'}),'conditions','S')
