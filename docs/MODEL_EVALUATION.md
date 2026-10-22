# 模型运行框架

## 1. 模型选择

LongSafety中的原模型清单以文本模型为主。本项目的输入包含多轮图片，因此实验模型必须支持多图对话。首个本地主基线使用`Qwen/Qwen2.5-VL-7B-Instruct`，第二架构校验使用`HuggingFaceTB/SmolVLM2-2.2B-Instruct`。后续模型应在相同运行协议下接入。

本地设备为16 GB显存时，Qwen2.5-VL-7B使用NF4 4-bit量化，并把单张图片控制在约128至512个视觉token对应的像素预算内。正式比较时必须记录每个模型实际处理的文本和视觉token，不能静默截断。

## 2. 框架分层

- `dataset.py`：读取JSONL、筛选轨道或样本并检查图片；
- `models/`：统一模型接口，本地模型和远程API各自实现适配器；
- `runner.py`：维护多轮消息历史、逐轮调用模型并保存结果；
- `configs/models/`：模型和量化参数；
- `configs/runs/`：一次实验使用的数据、样本和生成参数；
- `outputs/`：模型原始回答与运行元数据，不纳入Git。

## 3. 历史模式

- `interactive`：每轮都调用待测模型，并把其回答加入后续历史。静态和动态风险轨道默认使用该模式。
- `fixed_reference`：在MMDU良性轨道中重放前序参考回答，只让待测模型回答目标轮，用于固定上下文和诊断过度拒答。

## 4. 首次烟雾测试

```powershell
python scripts/run_experiment.py --config configs/runs/smoke_mock.json --dry-run
python scripts/run_experiment.py --config configs/runs/smoke_mock.json
python scripts/run_experiment.py --config configs/runs/smoke_qwen2_5_vl.json
```

Qwen烟雾测试包含同一个MMDS场景的安全/危险版本，各4轮。测试目标是确认模型加载、多图输入、多轮历史、确定性生成、token统计、显存统计和输出保存均能正常工作，不据此报告正式实验结论。

使用本地缓存离线复现Qwen测试：

```powershell
$env:HF_HOME=(Resolve-Path .).Path + '\.cache\huggingface'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
python scripts/run_experiment.py --config configs/runs/smoke_qwen2_5_vl.json
```

本机已完成2条对话、8次模型调用的真实运行。前三轮反事实前缀回答逐字一致，峰值显存约6.47 GB；详细配置、逐轮指标和初步现象见`data/reports/smoke_qwen25vl.md`。

随后完成了14条样本、64次真实模型调用的扩展预实验，覆盖三条数据轨道、四类风险以及短/中/长上下文。全部样本成功完成，最大实际输入为13,237 tokens，峰值显存约8.26 GB。当前主要问题是512-token生成上限造成59.4%的逐轮输出截断；详细结果见`data/reports/pilot_qwen25vl_expanded.md`。

## 5. 输出

每条对话保存为独立JSON文件，记录：

- 样本、条件、轨道和标签；
- 每轮风险状态与预期行为；
- 模型原始回答；
- 输入和输出token数；
- 是否达到最大生成长度而被截断；
- 推理时间和峰值显存；
- 模型配置、历史模式和生成参数。

后续的安全分类、拒答识别和人工复核从这些原始输出读取，不在推理阶段直接修改模型回答。

## 6. 固定校准协议v4

正式实验沿用下列确定性生成条件：

- 每轮追加中性的长度约束：回答不超过120个英文词；
- `max_new_tokens=384`、`do_sample=false`；
- `repetition_penalty=1.05`、`no_repeat_ngram_size=5`；
- 攻击轨道使用`interactive`历史，良性MMDU轨道使用`fixed_reference`历史；
- 每个样本单独落盘，失败样本单独记录并允许`--resume`续跑。

v4在Qwen2.5-VL上完成14条轨迹、84次生成，最终轮和全部调用均无截断；在SmolVLM2上完成相同规模的跨架构校验，最终轮无截断，存在2次成对一致的中间轮超长枚举截断。两模型的5组安全/危险配对均保持共享前缀回答逐字一致。详细结果见`data/reports/protocol_v4_readiness.md`。

Qwen2.5-VL作为首轮正式实验主基线；SmolVLM2用于确认数据和运行框架不绑定单一模型架构，其非最终轮截断必须在结果报告中保留。校准提示只控制回答格式，不作为安全防护方法，也不计入实验自变量。
