#!/usr/bin/env python3
"""Generate the formal_v3 organization and statistics report."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "processed" / "formal_v3.jsonl"
SEEDS = ROOT / "data" / "seeds" / "formal_v3_seed_bank.json"
VALIDATION = ROOT / "documentation" / "reports" / "formal_v3_validation.json"
MANIFEST = ROOT / "data" / "processed" / "formal_v3_shards" / "manifest.json"
OUTPUT = ROOT / "documentation" / "reports" / "formal_v3_stats.md"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rows(counter: Counter[str]) -> str:
    return "\n".join(f"| `{key}` | {value:,} |" for key, value in sorted(counter.items()))


def main() -> None:
    records = load_jsonl(DATASET)
    bank = load(SEEDS)
    validation = load(VALIDATION)
    manifest = load(MANIFEST)
    harmful = [item for item in records if item["track"] == "harmful_controlled"]
    benign = [item for item in records if item["track"] == "benign_controlled"]
    seed_image_counts = Counter(
        str(len(seed["evidence_packets"])) for seed in bank["harmful"] + bank["benign"]
    )
    token_ranges: dict[str, tuple[int, int]] = {}
    for bucket in ["2k", "8k", "16k"]:
        values = [item["context_stats"]["estimated_tokens"] for item in records if item["variables"]["context_bucket"] == bucket]
        token_ranges[bucket] = (min(values), max(values))

    shard_lines = "\n".join(
        f"| `{item['compressed_path']}` | {item['record_count']:,} | {item['compressed_bytes'] / 1024 / 1024:.2f} MiB | `{item['compressed_sha256']}` |"
        for item in manifest["files"]
    )
    text = f"""# `formal_v3` 数据集组织与统计

> 生成状态：结构验证通过，机器构造完成，人工双人审校未完成
> 生成日期：2026-10-23

## 1. 总体规模

| 项目 | 数量 |
|---|---:|
| 独立危险语义种子 | {len(bank['harmful']):,} |
| 独立良性语义种子 | {len(bank['benign']):,} |
| 独立语义种子合计 | {len(bank['harmful']) + len(bank['benign']):,} |
| 危险受控轨迹 | {len(harmful):,} |
| 良性受控轨迹 | {len(benign):,} |
| 轨迹总数 | {len(records):,} |
| 安全/危险最小差异对 | {validation['dataset']['safe_unsafe_pair_count']:,} |
| 静态/动态证据时序对 | {validation['dataset']['schedule_pair_count']:,} |

轨迹数是同一种子上的重复测量，统计独立单位是144个`seed_id`，不是4,224行JSONL。

## 2. 两层数据结构

危险层公式：`80 seeds × 12 conditions × 2 schedules × 2 labels = 3,840`。
良性层公式：`64 seeds × 3 lengths × 2 schedules = 384`。

### 风险类别轨迹

| 风险类别 | 轨迹数 |
|---|---:|
{rows(Counter(item['risk_category'] for item in harmful))}

### 危险子类型种子

| 危险子类型 | 独立种子数 |
|---|---:|
{rows(Counter(item['risk_subcategory'] for item in bank['harmful']))}

### 良性任务子类型种子

| 良性任务子类型 | 独立种子数 |
|---|---:|
{rows(Counter(item['benign_subcategory'] for item in bank['benign']))}

## 3. 数据划分

危险种子：calibration 8、primary 56、heldout 16；每个风险类别分别为2、14、4。
良性种子：calibration 8、primary 40、heldout 16。
所有条件变体按`seed_id`继承划分，同一种子绝不跨划分。

## 4. 视觉证据时序

| 时序 | 轨迹数 | 定义 |
|---|---:|---|
| `static_initial_bundle` | 2,112 | 全部唯一图片只在第一轮同时出现 |
| `dynamic_incremental` | 2,112 | 完全相同的图片集合分散到不同轮次，各出现一次 |

静态/动态配对共享用户文本、助手参考历史、标签、条件和图片集合，唯一变化是图片所在轮次。跨种子图片复用数为0。

## 5. 条件配置

危险层每个`C00`至`C11`均为320条。参考条件为6轮、8K、中间风险位置、渐进风险分布、图文互补和意图逐步升级；其他条件分别改变轮数、长度、风险位置、风险分布、图文关系或意图轨迹。

良性层的`B02`、`B08`、`B16`各128条，只控制2K/8K/16K长度和视觉证据时序。

实际估算token范围：2K为{token_ranges['2k'][0]:,}–{token_ranges['2k'][1]:,}，8K为{token_ranges['8k'][0]:,}–{token_ranges['8k'][1]:,}，16K为{token_ranges['16k'][0]:,}–{token_ranges['16k'][1]:,}；相对目标最大偏差为{validation['dataset']['max_relative_token_deviation'] * 100:.3f}%。

## 6. 配对组织

- `pair_id`连接同一条件和证据时序下的安全/危险最终请求；
- `schedule_pair_id`连接同一条件、标签下的静态/动态版本；
- 安全/危险对除最终请求及其最终轮gold标签外，共享前缀和图片；
- 静态/动态对共享全部文本和图片集合，只改变图片轮次；
- 每张图片在一条轨迹中只出现一次。

## 7. 图片组织

危险种子严格使用3至4个唯一视觉证据包。良性种子使用2至4个；其中2图良性种子只用于补足MMDU来源池中64个独立场景，未通过复制、裁剪或拼接无关图片凑数。证据包数量分布如下：

| 每种子证据包数 | 种子数 |
|---|---:|
{rows(seed_image_counts)}

数据集共记录{validation['dataset']['image_reference_count']:,}次轨迹级图片引用。

## 8. 文件与分片

| 文件 | 记录数 | 大小 | SHA-256 |
|---|---:|---:|---|
{shard_lines}

完整单文件为`data/processed/formal_v3.jsonl`，大小{validation['files']['dataset_bytes'] / 1024 / 1024:.2f} MiB，SHA-256为`{validation['files']['dataset_sha256']}`。推荐日常使用`.jsonl.gz`压缩分片和`manifest.json`；未压缩分片与完整单文件都可由构建脚本重建，不提交Git。

## 9. 单条记录结构

顶层字段包括：`sample_id`、`pair_id`、`schedule_pair_id`、`seed_id`、`split`、`condition_id`、`track`、`label`、风险/良性子类型、`variables`、`context_stats`、`source`、`turns`、`evaluation_target`和`construction`。

`turns[*]`包含用户文本、图片路径、固定助手历史以及逐轮描述性gold字段。gold字段用于构造检查和后续人工分析，不是已学习的风险分数。

## 10. 解释边界

当前版本已通过规模、配额、文件存在、图片唯一性、长度、最小差异配对、静态/动态配对和哈希验证，但144个种子仍标记为`machine_constructed_unreviewed`。正式论文实验前必须由人工复核：来源许可、图片事实描述、子类型归属、独立场景判断、安全/危险语义对等以及图文冗余/冲突条件的自然度。不得伪造审校者或把机器构造状态描述为人工审定。
"""
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
