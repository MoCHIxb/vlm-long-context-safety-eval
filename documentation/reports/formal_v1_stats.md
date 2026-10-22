# Formal v1 数据集统计

- 数据集：`LongContextMultiTurnVLMSafety-Formal-v1`
- 样本总数：456
- SHA-256：`6c86e8ce84d55d33bafffb72ab25e55db790a782b920b3fafeb35ace56ddf830`
- 文件大小：19.99 MiB

## 轨道与标签

| 项目 | 数量 |
|---|---:|
| `benign_multi_image_control` | 32 |
| `dynamic_risk_trajectory` | 160 |
| `static_visual_anchor` | 264 |
| 标签 `safe` | 244 |
| 标签 `unsafe` | 212 |

## 风险类别

| 类别 | 数量 |
|---|---:|
| `deception_and_economic_harm` | 106 |
| `illegal_and_cyber_abuse` | 106 |
| `none` | 32 |
| `physical_and_public_safety` | 106 |
| `privacy_and_profiling` | 106 |

## 实验因素覆盖

| 因素 | 数量 |
|---|---:|
| `benign_control` | 32 |
| `context_length` | 80 |
| `image_timing` | 16 |
| `intent_clarification` | 16 |
| `modality_relation` | 48 |
| `reference` | 40 |
| `risk_distribution` | 64 |
| `risk_position` | 80 |
| `turn_count` | 80 |

| 对话轮数 | 数量 |
|---:|---:|
| 4 | 56 |
| 6 | 344 |
| 8 | 56 |

## 长度控制

| 档位 | 样本数 | 目标token | 最小估计 | 最大估计 |
|---|---:|---:|---:|---:|
| `short` | 40 | 2048 | 2027 | 2086 |
| `medium` | 344 | 8192 | 8171 | 8230 |
| `long` | 40 | 16384 | 16363 | 16422 |

## 条件单元

| 轨道 | 条件 | 检验因素 | 每单元样本数 |
|---|---|---|---:|
| `benign_multi_image_control` | `B04-context_switch` | `benign_control` | 8 |
| `benign_multi_image_control` | `B04-continuation` | `benign_control` | 8 |
| `benign_multi_image_control` | `B08-context_switch` | `benign_control` | 8 |
| `benign_multi_image_control` | `B08-continuation` | `benign_control` | 8 |
| `dynamic_risk_trajectory` | `FD00` | `reference` | 16 |
| `dynamic_risk_trajectory` | `FD01` | `turn_count` | 16 |
| `dynamic_risk_trajectory` | `FD02` | `turn_count` | 16 |
| `dynamic_risk_trajectory` | `FD03` | `context_length` | 16 |
| `dynamic_risk_trajectory` | `FD04` | `context_length` | 16 |
| `dynamic_risk_trajectory` | `FD05` | `risk_position` | 16 |
| `dynamic_risk_trajectory` | `FD06` | `risk_position` | 16 |
| `dynamic_risk_trajectory` | `FD07` | `risk_distribution` | 16 |
| `dynamic_risk_trajectory` | `FD08` | `intent_clarification` | 16 |
| `dynamic_risk_trajectory` | `FD09` | `image_timing` | 16 |
| `static_visual_anchor` | `FS00` | `reference` | 24 |
| `static_visual_anchor` | `FS01` | `turn_count` | 24 |
| `static_visual_anchor` | `FS02` | `turn_count` | 24 |
| `static_visual_anchor` | `FS03` | `context_length` | 24 |
| `static_visual_anchor` | `FS04` | `context_length` | 24 |
| `static_visual_anchor` | `FS05` | `risk_position` | 24 |
| `static_visual_anchor` | `FS06` | `risk_position` | 24 |
| `static_visual_anchor` | `FS07` | `risk_distribution` | 24 |
| `static_visual_anchor` | `FS08` | `risk_distribution` | 24 |
| `static_visual_anchor` | `FS09` | `modality_relation` | 24 |
| `static_visual_anchor` | `FS10` | `modality_relation` | 24 |
