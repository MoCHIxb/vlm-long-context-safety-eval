#!/usr/bin/env python3
"""Build the frozen public-source Qwen3 supplement; no model or API calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from longvision_eval.real_dialogue_supplement import build_release


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', action='store_true', required=True, help='Explicitly rebuild derived public-source release files')
    p.parse_args()
    manifest=build_release(ROOT)
    print(json.dumps(dict(manifest='data/releases/real_dialogue_v1/manifest.json', **manifest['summary'])))


if __name__=='__main__':
    main()
