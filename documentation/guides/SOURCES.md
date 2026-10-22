# 数据来源

## SafeMT

- 论文：Zhu et al., *SafeMT: Multi-turn Safety for Multimodal Language Models*, ACL 2026.
- 数据仓库：<https://huggingface.co/datasets/HappyCorpse/SafeMT>
- 本项目用途：基础风险问题、场景类别和图像。
- 数据仓库标示许可：CC BY-NC 4.0。
- 本地种子保留原始`row`、`id`和图片路径，便于追溯。

## MTMCS-Bench

- 论文：Liu et al., *MTMCS-Bench: Evaluating Contextual Safety of Multimodal Large Language Models in Multi-Turn Dialogues*, Findings of ACL 2026.
- 论文页面：<https://aclanthology.org/2026.findings-acl.96/>
- 本项目用途：借鉴风险升级、上下文切换和安全/危险配对结构。
- 当前版本没有复制或声称使用其未取得的原始数据。

## LongSafety

- 论文：Lu et al., *LongSafety: Evaluating Long-Context Safety of Large Language Models*, ACL 2025.
- 代码与数据：<https://github.com/thu-coai/LongSafety>
- 本项目用途：借鉴长上下文长度控制与短/长条件比较思路。
- `pilot_v1`暂时使用确定性中性背景材料，未复制LongSafety正文。

## MMDS / LLaVAShield

- 论文：Huang et al., *LLaVAShield: Safeguarding Multimodal Multi-Turn Dialogues in Vision-Language Models*, CVPR 2026.
- 数据仓库：<https://huggingface.co/datasets/leost233/MMDS>
- 本项目用途：`pilot_v2`动态风险轨迹的原始多轮用户提示、逐轮图片、风险维度和来源ID。
- 数据仓库标示许可：CC BY-NC 4.0。
- 本项目不把来源模型回答作为动态危险轨迹的固定历史，以免继承来源回答中的不安全内容。

## MMDU

- 论文：Liu et al., *MMDU: A Multi-Turn Multi-Image Dialog Understanding Benchmark and Instruction-Tuning Dataset for LVLMs*, NeurIPS 2024 Datasets and Benchmarks Track.
- 项目仓库：<https://github.com/Liuziyu77/MMDU>
- 数据仓库：<https://huggingface.co/datasets/laolao77/MMDU>
- 本项目用途：`pilot_v2`良性多图对照、自然长对话历史和良性话题切换。
- 数据仓库标示许可：CC BY-NC 4.0。
- 前序参考回答可作为固定历史重放；最终轮参考答案仅用于质量核查和后续评分设计。

## 版本说明

本数据集是基于公开种子进行的研究性派生与受控改写，不是SafeMT、MTMCS-Bench、LongSafety、MMDS或MMDU的官方子集版本。公开或共享派生数据前，应再次核查所有来源许可和图片再分发要求。

