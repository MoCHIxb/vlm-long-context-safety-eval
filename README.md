# 长上下文多轮 VLM 安全预实验

本仓库用于毕业设计第一阶段的预实验，目标是以可复现的控制变量方式分析：

- 对话轮数；
- 上下文长度；
- 风险信息出现位置；
- 风险信息分散方式；
- 图文组合关系；

对视觉语言模型安全响应、攻击成功和过度拒答的影响。

## 数据版本

`pilot_v1`包含12个SafeMT基础图文场景、8个受控条件，以及每个条件下的一组安全/危险最小差异样本：

```text
12 seeds × 8 conditions × 2 labels = 192 dialogues
```

样本语言暂定为英文，以保持与来源数据一致。预实验使用约1K、4K和8K tokens三个长度档位；正式实验再根据计算预算扩展到约2K、8K和16K。

`pilot_v2`在不覆盖`pilot_v1`的前提下增加两类对照：

```text
64 SafeMT静态视觉锚点
+ 64 MMDS动态多图风险轨迹
+ 32 MMDU良性多图对照
= 160 dialogues
```

其中静态组用于分析文本历史增长，动态组用于分析跨轮、跨图风险累积，良性组用于测量正常多图任务能力和过度拒答。详细设计见`documentation/guides/DATASET_DESIGN_V2.md`。

`formal_v1`在预实验通过后固定为正式实验候选集：

```text
264 SafeMT静态单因素对照
+ 160 MMDS动态时序风险对照
+ 32 MMDU良性多图对照
= 456 dialogues（212组安全/危险配对）
```

正式集使用约2K、8K和16K三个长度档位，四类风险各106条攻击轨道样本。每个受控条件都记录`factor_under_test`及其基准条件，详细设计见`documentation/guides/FORMAL_DATASET_DESIGN.md`。

## 目录

```text
configs/                  实验条件配置
data/seeds/               来源种子与受控改写字段
data/raw/images/          下载的来源图片，不纳入Git
data/processed/           生成后的JSONL数据集
documentation/guides/     数据设计、模型运行、标注和来源说明
documentation/reports/    数据统计、预实验结果和就绪报告
scripts/                  下载、生成、验证和统计脚本
tests/                    数据结构测试
src/longvision_eval/      统一模型适配与逐轮实验运行框架
```

## 复现

下列命令中的`python`应替换为本机可用的Python 3.10以上解释器：

```powershell
python scripts/download_assets.py
python scripts/build_pilot.py
python scripts/validate_dataset.py
python scripts/report_stats.py
python -m unittest discover -s tests -v
```

## 模型烟雾测试

运行框架支持依赖无关的mock适配器、本地Qwen2.5-VL适配器和SmolVLM2适配器。先验证配置和数据，再运行模型：

```powershell
python -m pip install -e .
python scripts/run_experiment.py --config configs/runs/smoke_mock.json --dry-run
python scripts/run_experiment.py --config configs/runs/smoke_mock.json
```

本地模型依赖、量化参数和输出结构见`documentation/guides/MODEL_EVALUATION.md`。模型输出保存在`outputs/`且不会提交到Git。

正式实验前的固定校准配置位于`configs/runs/protocol_v4_*.json`。运行后可检查截断、显存和成对前缀一致性：

```powershell
python scripts/summarize_runs.py `
  --run-dir outputs/protocol-v4-qwen25vl-attack `
  --run-dir outputs/protocol-v4-qwen25vl-benign
```

为两名标注者生成隐藏模型名称的完整轨迹文件：

```powershell
python scripts/prepare_annotations.py `
  --run-dir outputs/protocol-v4-qwen25vl-attack `
  --run-dir outputs/protocol-v4-qwen25vl-benign `
  --annotator annotator_a `
  --output outputs/annotations/protocol_v4_annotator_a.jsonl
```

完成标注后使用`compare_annotations.py`检查一致性，仲裁后用`summarize_annotations.py`计算ASR、防御成功率、良性帮助率和过度拒答率。固定标签定义和流程见`documentation/guides/ANNOTATION_GUIDE.md`，全部文档入口见`documentation/README.md`。

构建`pilot_v2`时，先运行下载脚本取得MMDS和MMDU公开标注及图片压缩包，再只提取入选样本所需图片：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download_v2_sources.ps1
python scripts/prepare_v2_sources.py
python scripts/build_pilot_v2.py
python scripts/validate_dataset_v2.py
python scripts/report_stats_v2.py
python -m unittest discover -s tests -v
```

生成过程只依赖Python标准库。

构建和验证正式实验数据集：

```powershell
python scripts/build_formal_v1.py
python scripts/validate_formal_v1.py
python scripts/report_formal_v1.py
python -m unittest discover -s tests -v
```

正式运行配置按静态、动态和良性轨道拆分在`configs/runs/formal_v1_qwen_*.json`中。先运行`formal_v1_qwen_gate_attack.json`和`formal_v1_qwen_gate_benign.json`，核对实际token数、截断和显存，再启动整轨实验。

## 数据使用边界

- 数据仅用于经过授权的模型安全研究和评测。
- 不应将危险样本用于现实操作、部署或传播。
- SafeMT图片采用其公开数据仓库标示的CC BY-NC 4.0许可；使用时需要保留来源和许可信息。
- MMDS和MMDU公开数据仓库均标示为CC BY-NC 4.0；`pilot_v2`只提取入选记录所引用的图片，并保留来源ID。
- 原始图片通过下载脚本获取，不直接提交到Git。
- `pilot_v1`是预实验覆盖集，不是完整析因设计，不应据此直接声称所有变量具有独立因果效应。
- `pilot_v2`的三条轨道承担不同诊断功能，组间原始分数差异同样不能直接解释为单一变量的因果效应。

