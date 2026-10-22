#!/usr/bin/env python3
"""Create a compact Markdown data report for the generated pilot set."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "pilot_v1.jsonl"
REPORT_PATH = ROOT / "documentation" / "reports" / "pilot_v1_stats.md"


def table(counter: Counter[str], left: str) -> str:
    rows = [f"| {left} | 样本数 |", "|---|---:|"]
    rows.extend(f"| {key} | {value} |" for key, value in sorted(counter.items()))
    return "\n".join(rows)


def main() -> None:
    records = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    categories = Counter(record["risk_category"] for record in records)
    conditions = Counter(record["condition_id"] for record in records)
    labels = Counter(record["label"] for record in records)
    turns = Counter(str(record["variables"]["turn_count"]) for record in records)
    buckets = Counter(record["variables"]["context_bucket"] for record in records)
    modalities = Counter(record["variables"]["modality_relation"] for record in records)
    min_tokens = min(record["context_stats"]["estimated_tokens"] for record in records)
    max_tokens = max(record["context_stats"]["estimated_tokens"] for record in records)

    content = f"""# Pilot v1 数据统计

- 样本总数：{len(records)}
- 最小差异配对：{len(records) // 2}
- 基础场景：{len(set(record['seed_id'] for record in records))}
- 受控条件：{len(conditions)}
- 估算上下文范围：{min_tokens}–{max_tokens} tokens

## 标签

{table(labels, '标签')}

## 风险类别

{table(categories, '风险类别')}

## 条件

{table(conditions, '条件')}

## 对话轮数

{table(turns, '用户轮数')}

## 上下文长度

{table(buckets, '长度档位')}

## 图文关系

{table(modalities, '图文关系')}

## 说明

本报告统计的是预实验覆盖情况。八个条件用于验证实验管线和发现明显失效模式，并非完整因子设计；不能仅依据本预实验估计所有变量的独立主效应。
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(content, encoding="utf-8", newline="\n")
    print(f"Wrote report to {REPORT_PATH}")


if __name__ == "__main__":
    main()

