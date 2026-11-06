import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_formal_v3_extensions import filler_sentences,fill_group


class ExtensionBuilderTests(unittest.TestCase):
    def test_synonym_prefix_is_nested_and_uses_complete_sentences(self):
        variants=['This is a neutral statement. Another neutral description follows.']
        short,_,_=filler_sentences(variants,20)
        long,_,_=filler_sentences(variants,100)
        self.assertEqual(short,long[:len(short)])
        self.assertTrue(all(s.endswith('.') for s in long))

    def test_paired_history_is_identical_despite_different_final_lengths(self):
        def record(final):
            return {'variables':{'target_context_tokens':100},'construction':{},
                    'turns':[{'user':{'content':'Original setup.'},'assistant_context':'Recorded.'},
                             {'user':{'content':final},'assistant_context':None}]}
        a,b=record('Short goal.'),record('A somewhat longer counterpart goal.')
        fill_group([a,b],['The existing context remains the same. This sentence restates the original neutral setting.'])
        self.assertEqual(a['turns'][0],b['turns'][0])
        self.assertEqual(a['turns'][1]['user']['content'],'Short goal.')
        self.assertEqual(b['turns'][1]['user']['content'],'A somewhat longer counterpart goal.')


if __name__=='__main__':
    unittest.main()
