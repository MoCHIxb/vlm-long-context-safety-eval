# Pilot v2 数据统计

- 样本总数：160
- 安全/危险最小差异对：64
- 静态视觉基础场景：8
- 动态风险基础场景：8
- 良性多图基础场景：8
- 受控长上下文估算范围：1003-8230 tokens
- MMDU 固定参考历史估算范围：987-4586 tokens

## 三条数据轨道

| 轨道 | 样本数 |
|---|---:|
| benign_multi_image_control | 32 |
| dynamic_risk_trajectory | 64 |
| static_visual_anchor | 64 |

## 标签

| 标签 | 样本数 |
|---|---:|
| safe | 96 |
| unsafe | 64 |

## 风险类别

| 风险类别 | 样本数 |
|---|---:|
| deception_and_economic_harm | 32 |
| illegal_and_cyber_abuse | 32 |
| none | 32 |
| physical_and_public_safety | 32 |
| privacy_and_profiling | 32 |

## 条件

| 条件 | 样本数 |
|---|---:|
| B04-context_switch | 8 |
| B04-continuation | 8 |
| B08-context_switch | 8 |
| B08-continuation | 8 |
| D01 | 16 |
| D02 | 16 |
| D03 | 16 |
| D04 | 16 |
| P03 | 16 |
| P05 | 16 |
| P06 | 16 |
| P08 | 16 |

## 解释边界

`static_visual_anchor`用于识别文本历史增长时安全能力是否变化；`dynamic_risk_trajectory`用于识别跨轮、跨图证据累积导致的风险升级或遗忘；`benign_multi_image_control`用于估计正常多图理解能力和过度拒答。三条轨道承担不同诊断功能，不应把轨道之间的原始分数差异直接解释为单一变量的因果效应。
