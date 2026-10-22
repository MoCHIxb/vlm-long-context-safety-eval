#!/usr/bin/env python3
"""Write a compact, reproducible statistical report for formal_v1."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "formal_v1.json"
DATASET_PATH = ROOT / "data" / "processed" / "formal_v1.jsonl"
REPORT_PATH = ROOT / "documentation" / "reports" / "formal_v1_stats.md"


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data = DATASET_PATH.read_bytes()
    records = [json.loads(line) for line in data.decode("utf-8").splitlines() if line]
    track_counts = Counter(record["track"] for record in records)
    label_counts = Counter(record["label"] for record in records)
    category_counts = Counter(record["risk_category"] for record in records)
    factor_counts = Counter(record["variables"]["factor_under_test"] for record in records)
    turn_counts = Counter(record["variables"]["turn_count"] for record in records)

    lines = [
        "# Formal v1 数据集统计",
        "",
        f"- 数据集：`{config['dataset_name']}`",
        f"- 样本总数：{len(records)}",
        f"- SHA-256：`{hashlib.sha256(data).hexdigest()}`",
        f"- 文件大小：{len(data) / (1024 * 1024):.2f} MiB",
        "",
        "## 轨道与标签",
        "",
        "| 项目 | 数量 |",
        "|---|---:|",
    ]
    for key, value in sorted(track_counts.items()):
        lines.append(f"| `{key}` | {value} |")
    for key, value in sorted(label_counts.items()):
        lines.append(f"| 标签 `{key}` | {value} |")

    lines.extend(["", "## 风险类别", "", "| 类别 | 数量 |", "|---|---:|"])
    for key, value in sorted(category_counts.items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(["", "## 实验因素覆盖", "", "| 因素 | 数量 |", "|---|---:|"])
    for key, value in sorted(factor_counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "| 对话轮数 | 数量 |", "|---:|---:|"])
    for key, value in sorted(turn_counts.items()):
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## 长度控制",
            "",
            "| 档位 | 样本数 | 目标token | 最小估计 | 最大估计 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for bucket in ("short", "medium", "long"):
        values = [
            record["context_stats"]["estimated_tokens"]
            for record in records
            if record["variables"]["context_bucket"] == bucket
        ]
        lines.append(
            f"| `{bucket}` | {len(values)} | {config['token_estimation'][bucket]} | {min(values)} | {max(values)} |"
        )

    lines.extend(["", "## 条件单元", "", "| 轨道 | 条件 | 检验因素 | 每单元样本数 |", "|---|---|---|---:|"])
    condition_counts = Counter((record["track"], record["condition_id"]) for record in records)
    factors = {
        (record["track"], record["condition_id"]): record["variables"]["factor_under_test"]
        for record in records
    }
    for key, count in sorted(condition_counts.items()):
        lines.append(f"| `{key[0]}` | `{key[1]}` | `{factors[key]}` | {count} |")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
