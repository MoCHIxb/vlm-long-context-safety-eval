#!/usr/bin/env python3
"""Write the reproducible statistics report for formal_v2."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "formal_v2.jsonl"
REPORT_PATH = ROOT / "documentation" / "reports" / "formal_v2_stats.md"


def table(counter: Counter) -> list[str]:
    return [f"| `{key}` | {value} |" for key, value in sorted(counter.items(), key=lambda item: str(item[0]))]


def main() -> None:
    data = DATASET_PATH.read_bytes()
    records = [json.loads(line) for line in data.decode("utf-8").splitlines() if line]
    tracks = Counter(record["track"] for record in records)
    labels = Counter(record["label"] for record in records)
    categories = Counter(record["risk_category"] for record in records)
    source_identities = {
        (record["source"]["dataset"], str(record["source"].get("source_id", record["source"].get("row"))))
        for record in records
    }
    source_seeds = Counter()
    for track in tracks:
        source_seeds[track] = len({record["seed_id"] for record in records if record["track"] == track})
    conditions = Counter((record["track"], record["variables"]["context_bucket"]) for record in records)

    lines = [
        "# Formal v2 数据集统计", "",
        f"- 样本总数：{len(records)}", f"- 去重后的来源语义场景数：{len(source_identities)}",
        f"- SHA-256：`{hashlib.sha256(data).hexdigest()}`", f"- 文件大小：{len(data) / 1024 / 1024:.2f} MiB", "",
        "## 轨道规模", "", "| 轨道 | 样本数 |", "|---|---:|", *table(tracks), "",
        "| 轨道 | 独立语义种子 |", "|---|---:|", *table(source_seeds), "",
        "## 标签与风险类别", "", "| 标签 | 数量 |", "|---|---:|", *table(labels), "",
        "| 风险类别 | 数量 |", "|---|---:|", *table(categories), "",
        "## 长度条件", "", "| 轨道 / 长度档 | 数量 |", "|---|---:|",
    ]
    lines.extend(f"| `{track} / {bucket}` | {count} |" for (track, bucket), count in sorted(conditions.items()))
    lines.extend([
        "", "## 文献规模参照", "",
        "| 数据集 | 论文报告规模 | 与本数据集的关系 |", "|---|---:|---|",
        "| LongSafety（评测） | 1,543 | Formal v2 的 1,554 条与其处于同一评测规模 |",
        "| SafeMT | 10,000 | 含 2,000 个查询与 8,000 段生成对话，适合作为上限参照 |",
        "| MMDS | 4,484 | 含 2,756 个原始样本和 1,728 个增强样本；Formal v2 选取其中 192 个独立危险对话 |",
        "| SafeDialBench | 4,053 | 纯文本多轮安全基准，作为中等规模参照 |", "",
        "Formal v2 不以模板数量替代语义多样性：核心层用于单因素对照，扩展层用于检验结论能否跨场景成立。",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
