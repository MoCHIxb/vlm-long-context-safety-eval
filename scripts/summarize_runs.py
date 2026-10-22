from __future__ import annotations

import argparse
import json
from pathlib import Path

from longvision_eval.run_metrics import summarize_runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize runtime and truncation metrics.")
    parser.add_argument("--run-dir", action="append", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    summary = summarize_runs((root / path).resolve() for path in args.run_dir)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = (root / args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
