from __future__ import annotations

import argparse
import json
from pathlib import Path

from longvision_eval.annotation import summarize_annotations
from longvision_eval.dataset import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize completed human annotation labels.")
    parser.add_argument("annotation_file")
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    summary = summarize_annotations(load_jsonl((root / args.annotation_file).resolve()))
    rendered = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = (root / args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
