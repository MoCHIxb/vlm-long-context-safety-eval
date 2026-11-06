# 四模型本地部署

> 本文为历史部署准备记录。2026-11-06已开始本地Qwen正式推理，最新安排为Qwen完成后暂停，其余模型可在云端另行选择；以PROJECT_HANDOFF.md及[CLOUD_EXPERIMENT.md](CLOUD_EXPERIMENT.md)为准。

更新时间：2026-10-30。只准备权重与接口，不自动启动数据集实验；最终开始需用户通知审校完成、修订数据并冻结哈希。

## 模型与固定版本

| 标识 | 官方模型仓库 | 固定revision |
|---|---|---|
| qwen25vl7b | Qwen/Qwen2.5-VL-7B-Instruct | cc594898137f460bfe9f0759e9844b3ce807cfb5 |
| qwen3vl8b | Qwen/Qwen3-VL-8B-Instruct | 0c351dd01ed87e9c1b53cbc748cba10e6187ff3b |
| llava7b | llava-hf/llava-onevision-qwen2-7b-ov-hf | 0d50680527681998e456c7b78950205bedd8a068 |
| gemma3_12b | google/gemma-3-12b-it | 96b6f1eccf38110c56df3a15bffe176da04bfd80 |

Qwen3的计划名称从不存在于当前官方系列中的7B更正为8B。模型仅作参考对照，身份不参与数据集构造。2026-10-30用户已自行取得Gemma许可并完成本机HF登录，空间清理后四模型权重均完整缓存，离线CPU双图静态/动态与历史文本保留检查均通过。按用户要求尚未使用GPU；生成、长上下文资源和安全评测结果均待验证。

仓库计划：`configs/deployment/open_models.json`。运行配置由部署工具写入`configs/models/deployment/*_nf4.json`。不复用旧实验输出。

## 部署与检查

在仓库根目录运行：

```powershell
$env:PYTHONPATH = 'src'
# 只查看完整性；不联网、不加载模型。
.\.venv\Scripts\python.exe scripts/prepare_open_models.py

# 前三个模型下载与CPU检查的独立命令。Gemma命令见后文授权部分。
.\.venv\Scripts\python.exe scripts/prepare_open_models.py --model qwen25vl7b --model qwen3vl8b --model llava7b --download --processor-check

# GPU空闲后逐个加载；只回答临时红/蓝色图片的普通问题，不使用实验数据。
.\.venv\Scripts\python.exe scripts/prepare_open_models.py --model qwen25vl7b --model qwen3vl8b --model llava7b --processor-check --smoke
```

不写常驻推理服务。后续正式运行器按需加载模型，每次只运行一个进程/模型。部署锁防止两个部署命令并发；异常终止后若锁仍存在，应先核对进程再处理锁。

报告在`outputs/model_deployment/<模型标识>.json`，明确区分：权重完整、CPU预处理通过、GPU验证待完成、普通双图生成通过、磁盘不足、授权待处理。GPU阈值是保守启动门槛，不是16K适配完成的证明。用户未通知审校完成前，不启动全量安全评测。

工具验证所有索引分片、tokenizer与图片处理配置，并读取safetensors头；下载不表示逐张量数值校验。临时颜色图片检查后自动删除，不生成阅读稿预览图。部署报告不包含访问token。

## 显存、磁盘与精度

当前显卡为RTX 5070 Ti 16 GiB。四模型计划使用bitsandbytes NF4 4-bit、BF16计算、SDPA；报告中的安全结果应明确属于该量化配置，不能解释为原始BF16权重结果。12B与16K、多图组合是否可用，需要实际资源闸门验证。

下载使用仓库`.cache/huggingface`，禁用额外Xet缓存。新增三个模型原始safetensors约17.53、16.06、24.37 GB，另需小型配置和缓存空间。下载前保留至少8 GiB磁盘余量；不自动删除旧权重或移动其他文件。本次Gemma下载完成后D盘约余63.87 GiB，原有三个模型权重也已复核完整。

Qwen2.5与Qwen3采用各自patch规则下约256视觉token/图的处理预算；LLaVA保留原生图片处理，Gemma关闭pan-and-scan。各模型的视觉编码和实际token数并不完全相同，须记录配置和实际输入token。处理预算与NF4配置仍是待校准实验设置，正式运行前应固定，不得中途改变后混合统计。

## Gemma授权

用户在官方[Gemma页面](https://huggingface.co/google/gemma-3-12b-it)自行接受条款并取得访问权限，然后使用虚拟环境里的CLI在本机登录。不要将token粘贴到聊天或写入配置、Git。

```powershell
$env:HF_HOME = (Resolve-Path '.cache/huggingface').Path
.\.venv\Scripts\hf.exe auth login
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts/prepare_open_models.py --model gemma3_12b --include-gated --download --processor-check
```

其余官方来源：[Qwen3-VL](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct)、[LLaVA-OneVision](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-hf)。
