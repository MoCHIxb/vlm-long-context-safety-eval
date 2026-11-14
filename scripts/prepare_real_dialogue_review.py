#!/usr/bin/env python3
"""Prepare bounded, blind paired prefix review. Offline; no API/credential access."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from longvision_eval.dialogue_review import prepare_review


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True,type=Path,help='Imported complete run directory with manifest and checkpoints/results')
    p.add_argument('--output',required=True,type=Path,help='New preparation folder below outputs/')
    p.add_argument('--split',choices=['calibration','primary','heldout','all'],default='calibration')
    p.add_argument('--limit-trajectories',type=int,default=4)
    args=p.parse_args()
    if not 1<=args.limit_trajectories<=1408:p.error('limit-trajectories must be 1..1408')
    manifest=prepare_review(ROOT,ROOT/args.run,ROOT/args.output,
        ROOT/'configs/evaluation/real_dialogue_prefix_review_v1.json',split=args.split,limit_trajectories=args.limit_trajectories)
    print(json.dumps(dict(output=str(args.output),trajectories=len(manifest['sources']),
        observed_turns=len(manifest['mapping']),unique_requests=len(manifest['jobs']),
        input_requests=sum(j['phase']=='input' for j in manifest['jobs']),
        output_requests=sum(j['phase']=='output' for j in manifest['jobs']),network_requests=0)))


if __name__=='__main__':main()
