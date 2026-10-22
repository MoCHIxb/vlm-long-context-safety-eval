# Formal v2 正式实验数据集设计

## 1. 扩展依据

`formal_v1`的456条样本适合受控实验，但只有28个来源场景，无法单独支撑跨场景结论。参考文献中，LongSafety包含1,543个长上下文测试样例，SafeMT包含2,000个有害查询和8,000段生成对话，SafeDialBench包含4,053段多轮对话，MMDS包含4,484段对话，其中2,756条为原始样本、1,728条为增强样本。

因此，`formal_v2`将总规模扩展到1,554条，使其与LongSafety的纯评测规模基本一致。它不追求复刻SafeMT的10,000条规模，因为本课题还要对多个VLM逐轮推理、保存输出并进行人工复核，模型调用成本远高于只统计单轮样本数。

## 2. 两层结构

| 层次 | 样本数 | 独立来源 | 用途 |
|---|---:|---:|---|
| 核心受控层 | 456 | 28 | 单因素分析对话轮数、长度、风险位置、分散方式和图文关系 |
| MMDS风险覆盖层 | 768 | 192 | 在更多自然风险轨迹上检验长度效应和类别结论 |
| MMDU良性覆盖层 | 330 | 110 | 检验长上下文下的帮助能力和过度拒答 |
| 合计 | 1,554 | 322（跨层按来源去重） | 第一阶段正式评测 |

核心层完整继承`formal_v1`。扩展层不承担所有因素的因果识别，而用于检验核心层发现是否能推广到更多自然语义场景。

## 3. MMDS风险覆盖层

从MMDS原始、用户侧标为Unsafe的对话中选择192个独立场景，要求至少3个用户轮次和2张不同图片，并排除核心层已使用的8个MMDS场景。四类风险各选择48个场景；选择时按子类别轮询，降低只取某一子类别的偏差。

每个场景构造自然长度、约2K、8K和16K四个条件。用户输入、图片及其时序顺序保持不变。原始对话超过2K时，短条件仅压缩历史助手回答，不删除用户风险轮次或图片；需要扩展时，各长度条件使用同一中性背景序列的不同前缀。

该层的逐轮`risk_state`是依据原始轮次顺序生成的弱标注，只用于组织复核和描述性统计。关于某一轮风险发生变化的正式结论，应结合MMDS原始意图、理由字段和人工审核，不能把弱标注直接视为真实风险分数。

## 4. MMDU良性覆盖层

使用本地MMDU基准中的全部110个自然多图对话，统一截取前4个用户轮次，并构造约2K、8K和16K三个长度条件。各条件保留相同用户问题和图片，历史助手回答通过`fixed_reference`模式回放。该层只用于评估帮助率、拒答率和过度拒答率，不计算攻击成功率。

## 5. 运行与解释

核心层优先使用`interactive`模式观察目标模型自身响应如何沿轮次传播。扩展层优先使用`fixed_reference`模式固定最终轮之前的历史，从而避免不同模型早期回答差异污染长度比较。

建议采用两级实验：先运行核心层得到因素效应和失效模式，再在扩展层检验方向是否一致。统计时同时报告样本数、独立语义种子数、模型调用轮次数和有效输出数，不把同一场景的长度变体当作相互独立的语义样本。

扩展轨道已按`condition_id`提供独立运行配置。MMDS对应`MB00`至`MB03`，分别为自然、2K、8K和16K；MMDU对应`LB01`至`LB03`，分别为2K、8K和16K。每个分片均可使用`--resume`断点续跑。

构建脚本会根据`data/raw/formal_v2_source_checksums.json`核对MMDS与MMDU原始文件。若上游仓库更新导致校验失败，应先检查数据差异并显式更新版本记录，不能直接绕过校验后生成同名数据集。

构建与检查命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download_v2_sources.ps1
python scripts/build_formal_v2.py
python scripts/validate_formal_v2.py
python scripts/report_formal_v2.py
python -m unittest discover -s tests -v
```

文献规模来源：[LongSafety](https://aclanthology.org/2025.acl-long.1530/)、[SafeMT](https://aclanthology.org/2026.acl-long.1920/)、[SafeDialBench](https://proceedings.iclr.cc/paper_files/paper/2026/hash/cbd213baf0ad155f460ddee93f31d5ee-Abstract-Conference.html)及[MMDS/LLaVAShield](https://openaccess.thecvf.com/content/CVPR2026/html/Huang_LLaVAShield_Safeguarding_Multimodal_Multi-Turn_Dialogues_in_Vision-Language_Models_CVPR_2026_paper.html)。
