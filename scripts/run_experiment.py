#!/usr/bin/env python3
"""Run or validate a configured multi-turn VLM experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from longvision_eval.runner import execute


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = execute((root / args.config).resolve(), root, dry_run=args.dry_run, resume=args.resume)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
