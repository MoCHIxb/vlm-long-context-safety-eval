#!/usr/bin/env python3
"""CPU-only input-token/context check on the shared gate panel, without weights."""
import argparse
import gc
import json
from pathlib import Path
from datetime import datetime,timezone

from longvision_eval.runner import load_run,user_message,write_json_atomic
from longvision_eval.models.qwen_transformers import QwenTransformersAdapter
from longvision_eval.provenance import run_provenance

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args()
    run,model,records=load_run((ROOT/args.config).resolve(),ROOT)
    provenance=run_provenance(run,model,ROOT)
    from transformers import AutoProcessor,AutoConfig
    options={k:model[k] for k in ('revision','local_files_only','min_pixels','max_pixels') if k in model}
    processor=AutoProcessor.from_pretrained(model['model_name'],**options)
    architecture=AutoConfig.from_pretrained(model['model_name'],revision=model['revision'],local_files_only=True)
    context=getattr(getattr(architecture,'text_config',architecture),'max_position_embeddings',None)
    rows=[]
    for record in records:
        messages=[]
        for index,turn in enumerate(record['turns']):
            messages.append(user_message(turn,ROOT))
            if index<len(record['turns'])-1:
                if not turn['assistant_context']:
                    raise ValueError('Fixed reference history is empty')
                messages.append({'role':'assistant','content':turn['assistant_context']})
        converted=QwenTransformersAdapter._qwen_messages(messages)
        rendered=processor.apply_chat_template(converted,tokenize=False,add_generation_prompt=True)
        for message in converted:
            for item in message['content']:
                if item['type']=='text' and item['text'].strip() not in rendered:
                    raise ValueError('Chat template dropped source text')
        batch=processor.apply_chat_template(converted,tokenize=True,add_generation_prompt=True,
              return_dict=True,return_tensors='pt',processor_kwargs=model.get('processor_call_options',{}))
        count=int(batch['input_ids'].shape[-1])
        within=not context or count+run['generation']['max_new_tokens']<=context
        rows.append({'sample_id':record['sample_id'],'input_tokens':count,'within_context':within,
                     'nominal_target_tokens':record['variables']['target_context_tokens']})
        del batch
        gc.collect()
    result={'passed':all(r['within_context'] for r in rows),'model_id':model['model_id'],
       'model_name':model['model_name'],'revision':model['revision'],'samples_checked':len(rows),
       'scope':'Shared gate panel only; all full-run inputs are checked individually by the adapter',
       'min_input_tokens':min(r['input_tokens'] for r in rows),'max_input_tokens':max(r['input_tokens'] for r in rows),
       'model_context_limit':context,'max_new_tokens':run['generation']['max_new_tokens'],
       'weights_loaded':False,'gpu_used':False,'provenance':provenance,
       'checked_at_utc':datetime.now(timezone.utc).isoformat(),'records':rows}
    path=ROOT/'outputs/formal_v3_18turn_runs/preflight'/f'{model["key"]}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    write_json_atomic(path,result)
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
