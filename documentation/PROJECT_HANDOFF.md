# 项目交接说明

> 更新时间：2026-10-22  
> 项目目录：`D:\papers\Graduation Project\vlm-long-context-safety-eval`  
> GitHub：`https://github.com/MoCHIxb/vlm-long-context-safety-eval`  
> 当前分支：`main`  
> 本文档用于让新的对话在不读取完整聊天历史的情况下继续工作。

## 1. 新对话快速入口

在新对话中可直接使用：

```text
请接手工作区中的 vlm-long-context-safety-eval 项目。
先阅读 documentation/PROJECT_HANDOFF.md，并检查 README.md、Git 状态和最近5条提交。
请先简要总结当前研究目标、数据版本、实验进度和下一步工作，再执行我的新要求。
不要把闸门测试或弱标注当作正式安全结论，也不要覆盖已有数据版本。
```

一分钟状态摘要：

- 毕设主题是长上下文多轮对话下的视觉语言模型安全性分析与防护；
- 当前主要进行第一阶段“安全性分析”，尚未进入第二阶段风险分数建模；
- 正式候选数据集为`formal_v2`，共1,554条对话、322个按来源去重的语义场景；
- Qwen2.5-VL的12条`formal_v2`资源闸门已全部成功，无失败和输出截断；
- 数据构建、验证、分片运行和人工标注工具已就绪；
- 下一步应先运行MMDS自然长度分片，再依次运行2K、8K、16K和良性对照；
- 尚未产生正式ASR、拒答率或失效模式结论，不能把预实验观察写成论文结论。

## 2. 毕设研究定位

课题名称为“长上下文多轮对话下的视觉语言模型安全性分析与防护研究”。最终收敛后的研究思路分为三个递进部分：

1. **长上下文多轮安全性分析**：研究上下文长度、对话轮数、风险位置、风险分散方式和图文组合关系如何影响VLM的安全响应、攻击成功和过度拒答，并总结安全失效模式。该部分是后续研究的前置基础，也是当前仓库正在实施的阶段。
2. **时序风险累积过程建模**：将每轮风险线索、风险类别、图文证据、用户意图变化和历史安全响应组织为连续风险轨迹，进一步研究风险升级、延续和良性话题切换。当前数据中的`risk_factors`只是第一阶段描述性字段，尚不是风险分数，也没有确定权重。
3. **安全判断稳定性验证**：验证风险累积策略能否降低危险输出，同时避免正常任务上的过度拒答。安全感知上下文压缩目前只作为一种实验验证条件，不作为需要深入完成的独立方法方向。

早期讨论曾把整体防护构想称为`LongVisionGuard`。其核心思想是维护跨轮、跨模态的风险状态，并在上下文增长或压缩时保留关键安全证据。该名称目前只是研究构想，不是已经实现或验证的系统。

课题正式文字材料位于项目父目录：

- `D:\papers\Graduation Project\开题报告 (1).md`：扩充后的开题报告版本；
- `D:\papers\Graduation Project\参考论文综述_长上下文多轮VLM安全性分析与防护.md`；
- `D:\papers\Graduation Project\毕设文献学习.md`；
- `D:\papers\Graduation Project\毕设2-长上下文多轮对话下的视觉语言模型安全性分析与防护研究-池墨.docx`；
- `D:\papers\Graduation Project\研究流程框图_长上下文多轮VLM安全.svg`及`.png`。

## 3. 文献工作脉络

工作区已经完成五篇核心文献的详细翻译和独立解读：

1. LongSafety：长上下文安全评测；
2. SafeMT：多轮多模态安全评测；
3. REVEAL：图像输入危害的多轮评测；
4. MemeSafetyBench：真实视觉内容安全；
5. LLaVAShield/MMDS：多模态多轮内容审核与自动红队。

`毕设文献学习.md`还整理了LongSafety对齐、many-shot jailbreak、JailbreakBench、HarmBench、SafetyBench、SALAD-Bench、XSTest、SafetyReminder、MTMCS-Bench、SafeDialBench、Immune及多篇ACL/CVPR/ICLR 2025-2026相关工作。PDF均位于项目父目录。新的对话若要讨论创新点，应优先检索该文件和对应PDF，不要只依赖本文档的简述。

已有研究带来的核心判断：

- 单轮和短上下文安全表现不能代表长上下文安全；
- 攻击意图可跨轮、跨图片分散，并在历史中逐步累积；
- 只统计拒答不足以评价安全，还必须测量良性帮助和过度拒答；
- 防护需要保留时序风险证据，但不能机械继承早期敏感线索；
- 第一阶段实验必须有目的地支持第二阶段风险因素和权重设计。

## 4. 仓库结构与数据来源

主要目录：

```text
configs/                  数据、模型和运行配置
data/seeds/               预实验使用的来源种子
data/raw/                 原始元数据、压缩包和图片；大部分不提交Git
data/processed/           生成后的JSONL数据集
documentation/guides/     数据、模型和标注方法
documentation/reports/    统计、预实验和闸门报告
scripts/                  下载、构建、验证、运行和汇总脚本
src/longvision_eval/      模型适配器、数据选择和运行框架
tests/                    数据与运行框架测试
outputs/                  模型回答、错误和标注文件；不提交Git
```

主要数据来源：

- **SafeMT**：提供静态视觉锚点和有害查询场景；
- **MMDS**：提供风险意图随多轮、多图变化的自然危险轨迹；
- **MMDU**：提供自然良性多图对话，用于帮助率和过度拒答；
- **LongSafety**：主要参考长上下文长度控制和评测思路，不直接提供当前多模态图片。

原始MMDS和MMDU文件通过`scripts/download_v2_sources.ps1`下载。`formal_v2`构建时会使用`data/raw/formal_v2_source_checksums.json`核对SHA-256，防止上游`main`分支变化后静默生成不同数据。

## 5. 数据版本

### 5.1 `pilot_v1`

- 192条；
- 12个SafeMT场景 × 8个条件 × 安全/危险标签；
- 用于最早期控制变量和运行框架验证。

### 5.2 `pilot_v2`

- 160条；
- 64条SafeMT静态视觉锚点；
- 64条MMDS动态风险轨迹；
- 32条MMDU良性多图对照。

### 5.3 `formal_v1`

- 456条，212组安全/危险最小差异配对；
- 264条静态视觉锚点；
- 160条动态风险轨迹；
- 32条良性多图对照；
- 重点承担单因素受控分析。

### 5.4 `formal_v2`

当前正式候选集，完整包含`formal_v1`，规模如下：

| 层次 | 样本数 | 语义来源 | 作用 |
|---|---:|---:|---|
| 核心受控层 | 456 | 28 | 分析轮数、长度、风险位置、分散方式和图文关系 |
| MMDS风险覆盖层 | 768 | 192 | 192个危险对话 × 自然/2K/8K/16K |
| MMDU良性覆盖层 | 330 | 110 | 110个良性对话 × 2K/8K/16K |
| 合计 | 1,554 | 322（按来源去重） | 正式安全评测候选集 |

关键文件：

- `data/processed/formal_v2.jsonl`：65.02 MiB，GitHub已接收但提示超过推荐的50 MiB；
- `configs/formal_v2.json`：构建配置；
- `scripts/build_formal_v2.py`：确定性构建和图片提取；
- `scripts/validate_formal_v2.py`：规模、平衡、长度和图片验证；
- `scripts/report_formal_v2.py`：统计报告生成；
- `documentation/guides/FORMAL_V2_DATASET_DESIGN.md`：设计与解释边界；
- `documentation/reports/formal_v2_stats.md`：最终统计和数据哈希。

## 6. JSONL样本结构

每行保存一段完整对话。关键字段包括：

- `sample_id`：样本唯一标识；
- `pair_id`：安全/危险最小差异配对标识，没有配对时为`null`；
- `seed_id`、`condition_id`、`track`、`label`、`risk_category`；
- `variables`：轮数、长度档、风险位置、分散方式、模态关系和当前检验因素；
- `context_stats`：构建阶段的文本长度估计；
- `source`：来源数据集、来源ID、类别和原始意图；
- `turns`：按顺序保存每轮用户文本、图片、可选固定助手回答和描述性风险标注；
- `evaluation_target`：最终评测轮和安全/危险成功定义；
- `construction`：配对、轨迹和长度控制说明。

`turns[*].gold.risk_factors`目前包含：

- `risk_clue_strength`；
- `intent_explicitness`；
- `actionability_request`；
- `history_link_required`；
- `cross_modal_dependency`；
- `deescalation_evidence`。

这些字段用于第一阶段描述和后续人工分析。尤其是MMDS扩展层的逐轮风险状态属于依据轮次顺序生成的弱标注，不能直接作为第二阶段风险分数或真实权重。

## 7. 模型运行协议

当前支持：

- Qwen2.5-VL-7B-Instruct，NF4 4-bit，第一轮正式实验主基线；
- SmolVLM2-2.2B-Instruct，BF16，跨架构复核；
- mock适配器，用于无模型依赖的框架测试。

固定生成协议：

- `do_sample=false`；
- `max_new_tokens=384`；
- 回答约束为不超过120个英文词；
- `repetition_penalty=1.05`；
- `no_repeat_ngram_size=5`；
- 每个样本独立保存，失败单独记录；
- 使用`--resume`断点续跑。

历史模式：

- `interactive`：每轮都由待测模型生成，用于核心静态和动态风险轨道；
- `fixed_reference`：重放来源助手历史，只生成最终目标轮，用于MMDS/MMDU扩展层，以固定不同模型面对的上下文。

早期扩展预实验曾因模型反复枚举并达到512-token生成上限而出现大量截断。协议v4通过120词回答约束、384-token上限和轻量重复抑制解决了Qwen截断；这些设置只是可比性控制，不是安全防护方法。

## 8. 已完成实验

### 8.1 预实验与协议校准

- Qwen最小烟雾测试：多图、多轮、模型加载和结果落盘成功；
- 扩展预实验：确认三条轨道可运行，也暴露了输出截断问题；
- 协议v4：Qwen和SmolVLM2各完成14条轨迹；Qwen无截断，SmolVLM2有2次非最终轮截断，最终目标轮完整；
- 双人标注文件生成、匿名模型映射、Cohen's kappa、分歧仲裁和指标汇总工具已准备。

### 8.2 `formal_v2` Qwen资源闸门

2026-10-22完成12条实机闸门：

| 指标 | 结果 |
|---|---:|
| 成功/总样本 | 12/12 |
| 实际最终轮生成 | 12 |
| 失败 | 0 |
| 输出截断 | 0 |
| 最大实际输入token | 18,741 |
| 峰值GPU显存 | 9,355.03 MiB |
| 总生成耗时 | 97.78 s |

16K文本条件经过图片token、系统提示和聊天模板后，真实输入约17.1K至18.7K。资源上可以继续正式实验，但这12条不能用于报告ASR或安全优劣。详情见`documentation/reports/formal_v2_qwen_gate_report.md`。

## 9. 正式实验尚未完成的工作

推荐执行顺序：

1. 运行MMDS自然长度分片，先检查来源轨迹和标注流程；
2. 运行MMDS 2K、8K、16K分片；
3. 运行MMDU 2K、8K、16K良性分片；
4. 每个分片结束后检查失败、真实输入token、显存和截断；
5. 生成两名标注者的匿名标注文件；
6. 双人独立标注并计算一致性，对分歧仲裁；
7. 报告ASR、防御成功率、良性帮助率和过度拒答率；
8. 使用同一语义种子的重复测量或配对统计分析长度效应，不能把四个长度变体当作四个独立场景；
9. 根据定量结果和典型案例总结安全失效模式，为第二阶段风险因素权重提供依据；
10. 至少增加一个跨架构模型复核关键结论，避免只报告Qwen结果。

当前尚未决定第二阶段风险分数的具体公式、权重学习方式或干预阈值。应先完成第一阶段数据分析，再根据真实失效模式设计，避免用预设权重反过来解释数据。

## 10. 常用命令

在仓库目录执行：

```powershell
# 重新构建和验证formal_v2
python scripts/build_formal_v2.py
python scripts/validate_formal_v2.py
python scripts/report_formal_v2.py

# 测试
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v

# Qwen资源闸门
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_experiment.py `
  --config configs\runs\formal_v2_qwen_gate.json --resume

# 正式实验第一分片：MMDS自然长度
.\.venv\Scripts\python.exe scripts\run_experiment.py `
  --config configs\runs\formal_v2_qwen_mmds_natural.json --resume
```

其余分片配置：

```text
formal_v2_qwen_mmds_short.json
formal_v2_qwen_mmds_medium.json
formal_v2_qwen_mmds_long.json
formal_v2_qwen_mmdu_short.json
formal_v2_qwen_mmdu_medium.json
formal_v2_qwen_mmdu_long.json
```

运行完成后可使用：

```powershell
python scripts/summarize_runs.py --run-dir outputs\<run-id>
python scripts/prepare_annotations.py --run-dir outputs\<run-id> `
  --annotator annotator_a --output outputs\annotations\<name>.jsonl
python scripts/compare_annotations.py <标注者A文件> <标注者B文件>
python scripts/summarize_annotations.py <仲裁文件>
```

具体参数以各脚本的`--help`和`documentation/guides/ANNOTATION_GUIDE.md`为准。

## 11. 重要解释边界

- 安全研究数据仅用于授权评测，不用于现实危害操作；
- `formal_v1`核心层适合做组内单因素比较，扩展层主要检验推广性；
- 中性背景文本用于长度控制，不代表真实自然长对话分布；
- 构建阶段token是估计值，正式报告必须使用模型处理器记录的实际token；
- 样本标签描述目标请求，不等于模型回答标签；模型回答必须另行人工判定；
- 不应只用拒答关键词判断攻击成功或防御成功；
- 良性轨道与危险轨道承担不同指标，不能简单混合计算一个“安全率”；
- 闸门、烟雾测试和小规模校准只证明工程可运行，不能作为论文主要实验结论；
- 不要覆盖`pilot_v1`、`pilot_v2`、`formal_v1`或`formal_v2`，新设计应建立新版本；
- `outputs/`包含模型原始回答，不提交Git。

## 12. Git状态与提交脉络

创建本文档前，远程`main`与本地同步到：

```text
830cae4 Expand formal VLM safety evaluation dataset
980c18e Add formal multi-turn VLM safety dataset
f3e76ef Organize project documentation and reports
e4d56fc Prepare formal VLM safety evaluation protocol
dd18541 Record expanded Qwen pilot experiment
```

新对话开始工作前仍应执行`git status --short`和`git log -5 --oneline`，因为本文档可能晚于后续提交而失效。工作区可能包含用户尚未提交的修改，不能擅自回退或覆盖。
