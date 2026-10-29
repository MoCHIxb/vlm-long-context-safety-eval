# `formal_v3` 数据集组织与统计

> 生成状态：结构验证通过，机器构造完成，人工双人审校未完成
> 生成日期：2026-10-23

## 1. 总体规模

| 项目 | 数量 |
|---|---:|
| 独立危险语义种子 | 80 |
| 独立良性语义种子 | 64 |
| 独立语义种子合计 | 144 |
| 危险受控轨迹 | 3,840 |
| 良性受控轨迹 | 384 |
| 轨迹总数 | 4,224 |
| 安全/危险最小差异对 | 1,920 |
| 静态/动态证据时序对 | 2,112 |

轨迹数是同一种子上的重复测量，统计独立单位是144个`seed_id`，不是4,224行JSONL。

## 2. 两层数据结构

危险层公式：`80 seeds × 12 conditions × 2 schedules × 2 labels = 3,840`。
良性层公式：`64 seeds × 3 lengths × 2 schedules = 384`。

### 风险类别轨迹

| 风险类别 | 轨迹数 |
|---|---:|
| `deception_and_economic_harm` | 960 |
| `illegal_and_cyber_abuse` | 960 |
| `physical_and_public_safety` | 960 |
| `privacy_and_profiling` | 960 |

### 危险子类型种子

| 危险子类型 | 独立种子数 |
|---|---:|
| `aggregation_identification_and_doxxing` | 5 |
| `automation_api_abuse_and_service_disruption` | 5 |
| `confidentiality_breach_and_disclosure` | 5 |
| `credential_theft_and_account_abuse` | 5 |
| `dangerous_stunts_and_animal_harm` | 5 |
| `financial_or_document_fraud` | 5 |
| `health_and_public_misinformation` | 5 |
| `illicit_transactions_fraud_and_identity_abuse` | 5 |
| `impersonation_deepfake_and_social_engineering` | 5 |
| `malware_and_unauthorized_system_access` | 5 |
| `misleading_marketing_and_consumer_manipulation` | 5 |
| `surveillance_snooping_and_interrogation` | 5 |
| `targeted_assault_and_coercive_harm` | 5 |
| `terrorism_disaster_and_public_disruption` | 5 |
| `unauthorized_secondary_use_and_decisional_interference` | 5 |
| `weapons_and_violent_facilitation` | 5 |

### 良性任务子类型种子

| 良性任务子类型 | 独立种子数 |
|---|---:|
| `art_culture_and_history` | 8 |
| `defensive_safety_and_compliance` | 8 |
| `document_and_chart_understanding` | 8 |
| `education_and_scientific_explanation` | 8 |
| `everyday_assistance_and_content_creation` | 8 |
| `health_information_and_accessibility` | 8 |
| `navigation_planning_and_spatial_reasoning` | 8 |
| `product_scene_and_object_comparison` | 8 |

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

实际估算token范围：2K为2,048–2,052，8K为8,196–8,196，16K为16,388–16,388；相对目标最大偏差为0.195%。

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
| `2` | 7 |
| `3` | 54 |
| `4` | 83 |

数据集共记录14,850次轨迹级图片引用。

## 8. 文件与分片

| 文件 | 记录数 | 大小 | SHA-256 |
|---|---:|---:|---|
| `data/processed/formal_v3_shards/harmful_deception_and_economic_harm.jsonl.gz` | 960 | 2.69 MiB | `fc3fd47cba6cc1f028eae37a1379812d14c139478ee80dc29d8ad2cf2fa8e5e2` |
| `data/processed/formal_v3_shards/harmful_privacy_and_profiling.jsonl.gz` | 960 | 2.69 MiB | `78b0192cd05424ad0895d2269b4492a6cf2fdf7455e7586e6dbeedc02b1774da` |
| `data/processed/formal_v3_shards/harmful_illegal_and_cyber_abuse.jsonl.gz` | 960 | 2.69 MiB | `6aa2f62e1d7a40b91cf357324df52475d12017eaf6b3347bde0ef0d554a11afa` |
| `data/processed/formal_v3_shards/harmful_physical_and_public_safety.jsonl.gz` | 960 | 2.73 MiB | `735b555b3e57387ef4b92af2d04f1dc8cf4244e4a1263afba8a9267243ac6e90` |
| `data/processed/formal_v3_shards/benign_controlled.jsonl.gz` | 384 | 1.94 MiB | `f21558527a5f26412e8490e0640f6c6d59699e85abdc52f9c6af3230e3c5f2a5` |

完整单文件为`data/processed/formal_v3.jsonl`，大小194.46 MiB，SHA-256为`f96688c03415dfcb732230998f26be5d6d7c600cc1bd9c6c8d98a4259649e23e`。推荐日常使用`.jsonl.gz`压缩分片和`manifest.json`；未压缩分片与完整单文件都可由构建脚本重建，不提交Git。

## 9. 单条记录结构

顶层字段包括：`sample_id`、`pair_id`、`schedule_pair_id`、`seed_id`、`split`、`condition_id`、`track`、`label`、风险/良性子类型、`variables`、`context_stats`、`source`、`turns`、`evaluation_target`和`construction`。

`turns[*]`包含用户文本、图片路径、固定助手历史以及逐轮描述性gold字段。gold字段用于构造检查和后续人工分析，不是已学习的风险分数。

## 10. 解释边界

当前版本已通过规模、配额、文件存在、图片唯一性、长度、最小差异配对、静态/动态配对和哈希验证，但144个种子仍标记为`machine_constructed_unreviewed`。正式论文实验前必须由人工复核：来源许可、图片事实描述、子类型归属、独立场景判断、安全/危险语义对等以及图文冗余/冲突条件的自然度。不得伪造审校者或把机器构造状态描述为人工审定。
