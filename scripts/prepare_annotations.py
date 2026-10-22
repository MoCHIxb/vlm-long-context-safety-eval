from __future__ import annotations

import argparse
import json
from pathlib import Path

from longvision_eval.annotation import build_annotation_items, load_results, write_jsonl
from longvision_eval.dataset import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a blinded JSONL file for human annotation.")
    parser.add_argument("--dataset", default="data/processed/pilot_v2.jsonl")
    parser.add_argument("--run-dir", action="append", required=True)
    parser.add_argument("--annotator", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    records = load_jsonl(root / args.dataset)
    run_dirs = [(root / path).resolve() for path in args.run_dir]
    items, key = build_annotation_items(records, load_results(run_dirs), args.annotator)
    output = (root / args.output).resolve()
    write_jsonl(output, items)
    key_path = output.with_suffix(".key.json")
    key_path.write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(items), "output": str(output), "key": str(key_path)}, indent=2))


if __name__ == "__main__":
    main()
