from __future__ import annotations

import argparse
import json
from pathlib import Path

from longvision_eval.annotation import compare_annotation_sets
from longvision_eval.dataset import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure agreement between two annotation files.")
    parser.add_argument("annotation_a")
    parser.add_argument("annotation_b")
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    result = compare_annotation_sets(
        load_jsonl((root / args.annotation_a).resolve()),
        load_jsonl((root / args.annotation_b).resolve()),
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = (root / args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
