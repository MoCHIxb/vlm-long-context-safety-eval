# Pilot v1 数据统计

- 样本总数：192
- 最小差异配对：96
- 基础场景：12
- 受控条件：8
- 估算上下文范围：1006–8202 tokens

## 标签

| 标签 | 样本数 |
|---|---:|
| safe | 96 |
| unsafe | 96 |

## 风险类别

| 风险类别 | 样本数 |
|---|---:|
| deception_and_economic_harm | 48 |
| illegal_and_cyber_abuse | 48 |
| physical_and_public_safety | 48 |
| privacy_and_profiling | 48 |

## 条件

| 条件 | 样本数 |
|---|---:|
| P01 | 24 |
| P02 | 24 |
| P03 | 24 |
| P04 | 24 |
| P05 | 24 |
| P06 | 24 |
| P07 | 24 |
| P08 | 24 |

## 对话轮数

| 用户轮数 | 样本数 |
|---|---:|
| 2 | 24 |
| 4 | 48 |
| 6 | 48 |
| 8 | 72 |

## 上下文长度

| 长度档位 | 样本数 |
|---|---:|
| long | 72 |
| medium | 72 |
| short | 48 |

## 图文关系

| 图文关系 | 样本数 |
|---|---:|
| complementary | 48 |
| conflict_context_switch | 24 |
| image_dominant | 24 |
| redundant | 48 |
| text_only | 48 |

## 说明

本报告统计的是预实验覆盖情况。八个条件用于验证实验管线和发现明显失效模式，并非完整因子设计；不能仅依据本预实验估计所有变量的独立主效应。
