#!/usr/bin/env python3
"""Create the Markdown coverage report for pilot_v2."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "pilot_v2.jsonl"
REPORT_PATH = ROOT / "documentation" / "reports" / "pilot_v2_stats.md"


def table(counter: Counter[str], left: str) -> str:
    rows = [f"| {left} | 样本数 |", "|---|---:|"]
    rows.extend(f"| {key} | {value} |" for key, value in sorted(counter.items()))
    return "\n".join(rows)


def main() -> None:
    records = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    tracks = Counter(record["track"] for record in records)
    labels = Counter(record["label"] for record in records)
    categories = Counter(record["risk_category"] for record in records)
    conditions = Counter(record["condition_id"] for record in records)
    dynamic = [record for record in records if record["track"] == "dynamic_risk_trajectory"]
    benign = [record for record in records if record["track"] == "benign_multi_image_control"]
    controlled_tokens = [record["context_stats"]["estimated_tokens"] for record in records if record["variables"]["target_context_tokens"]]
    benign_reference_tokens = [record["context_stats"]["reference_history_estimated_tokens"] for record in benign]

    content = f"""# Pilot v2 数据统计

- 样本总数：{len(records)}
- 安全/危险最小差异对：{sum(1 for record in records if record['pair_id']) // 2}
- 静态视觉基础场景：{len(set(record['seed_id'] for record in records if record['track'] == 'static_visual_anchor'))}
- 动态风险基础场景：{len(set(record['seed_id'] for record in dynamic))}
- 良性多图基础场景：{len(set(record['seed_id'] for record in benign))}
- 受控长上下文估算范围：{min(controlled_tokens)}-{max(controlled_tokens)} tokens
- MMDU 固定参考历史估算范围：{min(benign_reference_tokens)}-{max(benign_reference_tokens)} tokens

## 三条数据轨道

{table(tracks, '轨道')}

## 标签

{table(labels, '标签')}

## 风险类别

{table(categories, '风险类别')}

## 条件

{table(conditions, '条件')}

## 解释边界

`static_visual_anchor`用于识别文本历史增长时安全能力是否变化；`dynamic_risk_trajectory`用于识别跨轮、跨图证据累积导致的风险升级或遗忘；`benign_multi_image_control`用于估计正常多图理解能力和过度拒答。三条轨道承担不同诊断功能，不应把轨道之间的原始分数差异直接解释为单一变量的因果效应。
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(content, encoding="utf-8", newline="\n")
    print(f"Wrote report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
