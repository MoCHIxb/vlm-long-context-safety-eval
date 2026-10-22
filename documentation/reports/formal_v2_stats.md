# Formal v2 数据集统计

- 样本总数：1554
- 去重后的来源语义场景数：322
- SHA-256：`28424be1a7004552268303e83482575154e231c4cdc7eac40222e833cfb7490d`
- 文件大小：65.02 MiB

## 轨道规模

| 轨道 | 样本数 |
|---|---:|
| `benign_multi_image_control` | 32 |
| `dynamic_risk_trajectory` | 160 |
| `mmds_breadth_length` | 768 |
| `mmdu_benign_length` | 330 |
| `static_visual_anchor` | 264 |

| 轨道 | 独立语义种子 |
|---|---:|
| `benign_multi_image_control` | 8 |
| `dynamic_risk_trajectory` | 8 |
| `mmds_breadth_length` | 192 |
| `mmdu_benign_length` | 110 |
| `static_visual_anchor` | 12 |

## 标签与风险类别

| 标签 | 数量 |
|---|---:|
| `safe` | 574 |
| `unsafe` | 980 |

| 风险类别 | 数量 |
|---|---:|
| `deception_and_economic_harm` | 298 |
| `illegal_and_cyber_abuse` | 298 |
| `none` | 362 |
| `physical_and_public_safety` | 298 |
| `privacy_and_profiling` | 298 |

## 长度条件

| 轨道 / 长度档 | 数量 |
|---|---:|
| `benign_multi_image_control / natural` | 32 |
| `dynamic_risk_trajectory / long` | 16 |
| `dynamic_risk_trajectory / medium` | 128 |
| `dynamic_risk_trajectory / short` | 16 |
| `mmds_breadth_length / long` | 192 |
| `mmds_breadth_length / medium` | 192 |
| `mmds_breadth_length / natural` | 192 |
| `mmds_breadth_length / short` | 192 |
| `mmdu_benign_length / long` | 110 |
| `mmdu_benign_length / medium` | 110 |
| `mmdu_benign_length / short` | 110 |
| `static_visual_anchor / long` | 24 |
| `static_visual_anchor / medium` | 216 |
| `static_visual_anchor / short` | 24 |

## 文献规模参照

| 数据集 | 论文报告规模 | 与本数据集的关系 |
|---|---:|---|
| LongSafety（评测） | 1,543 | Formal v2 的 1,554 条与其处于同一评测规模 |
| SafeMT | 10,000 | 含 2,000 个查询与 8,000 段生成对话，适合作为上限参照 |
| MMDS | 4,484 | 含 2,756 个原始样本和 1,728 个增强样本；Formal v2 选取其中 192 个独立危险对话 |
| SafeDialBench | 4,053 | 纯文本多轮安全基准，作为中等规模参照 |

Formal v2 不以模板数量替代语义多样性：核心层用于单因素对照，扩展层用于检验结论能否跨场景成立。
