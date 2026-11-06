# RTX4090云端部署与同步实验

## 运行分工

本地Qwen2.5-VL-7B继续当前4864条，完成后暂停并做技术检查。云端默认运行Qwen3-VL-8B，不复制或接续本地Qwen结果。可另行选择LLaVA或Gemma；同一台服务器仍一次只加载一个模型。不同服务器可以各运行一个不同模型。

云端沿用同一4864条、144种子、固定参考历史、NF4/BF16、贪心解码、1024输出上限和固定模型revision。只生成最后一轮回答，不是从头自由交互实验。云端run_id增加`-cloud`，保留硬件、软件和配置来源；不同硬件的速度和显存指标分别比较，不默认与本地相同。

## 系统与版本

- Linux x86_64，建议Ubuntu 22.04/24.04；RTX4090通常24GB，先用`nvidia-smi`核对实际显存和驱动。
- 本地实际版本：Python **3.14.6**、PyTorch **2.14.1+cu130**、PyTorch CUDA运行时 **13.0**、torchvision **0.29.1+cu130**；本地驱动610.88。驱动显示CUDA UMD 13.3不等于PyTorch使用13.3。
- 推荐云端使用Python 3.14；项目最低3.11，若使用其他Python小版本需能安装锁定依赖，环境报告会记录差异。
- 默认安装CUDA 13.0的PyTorch wheel，服务器驱动必须支持它。不需要另行编译CUDA工具链。若服务器驱动不兼容，应先选择兼容镜像/驱动；脚本不会自动更改驱动或静默改用CPU。
- `requirements-cloud.txt`锁定本地测得的主要推理包版本。脚本会停止于缺失wheel/依赖冲突，而不会偷偷降级。Linux安装及实际RTX4090资源检查须在服务器执行，本地仅完成脚本与数据恢复验证。
- 准备git、Python、venv模块；系统包安装由服务器用户处理。保留至少60GB空闲空间供单模型权重、wheel和结果；若下载全部模型，建议150GB以上。这是容量预留，不是实验峰值测量。

## 克隆与安装

```bash
git clone https://github.com/MoCHIxb/vlm-long-context-safety-eval.git
cd vlm-long-context-safety-eval
nvidia-smi
PYTHON_BIN=python3.14 bash scripts/cloud_experiment.sh setup
```

私有仓库需要在云服务器配置你自己的GitHub访问方式。不要将本机`.cache`、HF token、API key或DPAPI凭据上传。Python命令名不同可修改`PYTHON_BIN`。PyTorch的安装来源可通过`TORCH_INDEX_URL`显式调整，但仍要求相同torch/torchvision版本；修改CUDA构建属于环境差异，必须保留报告。

## 恢复数据、下载模型

```bash
bash scripts/cloud_experiment.sh prepare
bash scripts/cloud_experiment.sh download --model qwen3vl8b
```

`prepare`恢复Git中约11.8MB的固定压缩快照（解压后JSONL约240MB），重建并校验分类压缩分片，随后从MMDS/MMDU公开来源下载两份图片档案（共约459MB），只提取本协议用到的508张图片（约144MB），逐张核对SHA-256。最后执行独立数据校验。不调用生成API、不重新抽样数据、不读取本地模型回答。

如果上游变更导致档案哈希不一致，会停止。此时保留日志并查明来源版本，不要通过修改manifest绕过校验。来源许可记录保留，图片不作为新的无许可资产发布。

模型下载使用固定revision和CPU图片处理检查；真正的GPU生成及资源闸门在`run`阶段。需要访问受限仓库时，在云服务器单独登录HF；本机登录状态不会通过Git同步。

Gemma示例：

```bash
export HF_HOME="$PWD/.cache/huggingface"
.venv-cloud/bin/hf auth login
bash scripts/cloud_experiment.sh download --model gemma3_12b --include-gated
```

## 启动与断点续跑

先查看生成的计划（不加载GPU、不启动实验）：

```bash
bash scripts/cloud_experiment.sh plan --model qwen3vl8b
```

在tmux会话中保持运行，推荐默认只跑Qwen3：

```bash
tmux new -s vlm-cloud
bash scripts/cloud_experiment.sh run --model qwen3vl8b
```

顺序为CPU输入检查→双色图片GPU诊断→16条资源闸门→4864条正式结果。所有权重准备完成后离线推理；错误、不完整结果或明显系统性退化会阻止继续运行。输出截断会单独统计，不当作拒绝或安全回答。

如需云端顺序跑其他模型，必须先下载它们，再显式选择：

```bash
bash scripts/cloud_experiment.sh download --model llava7b
bash scripts/cloud_experiment.sh run --model qwen3vl8b --model llava7b
```

如中断，在确认旧控制器和模型进程均已退出后，以同样命令重启，内部使用`--resume`。如果留下`outputs/formal_v3_18turn_runs/serial_queue.lock`，先核对其中PID确实已不再运行，才能手动移除该锁；不要在活动进程运行时移除。不要把另一台服务器的状态文件和锁文件覆盖到当前服务器。

## 输出与回传

- 状态：`outputs/formal_v3_18turn_runs/queue_status.json`。
- 日志：同目录`logs/`；环境：`outputs/cloud_environment/`。
- 配置：`outputs/cloud_configs/`；正式结果：`outputs/formal_v3_18turn_runs/formal-v318-qwen3vl8b-ffd78bcc-ad9fe617-g1024-cloud/`。
- 每条结果`turns[-1].response.text`为实际最终回答；前面`Noted.`为固定参考。
- 每阶段结束写`technical_metrics.json`：失败、空答、重复标记、截断、最大输入token、显存、生成耗时。16条gate与正式结果不混合。

运行结束后打包需要回传的结果及环境记录，不包含凭据或模型权重：

```bash
tar -czf cloud-qwen3-results.tar.gz \
  outputs/formal_v3_18turn_runs/formal-v318-qwen3vl8b-ffd78bcc-ad9fe617-g1024-cloud \
  outputs/cloud_configs outputs/cloud_environment
sha256sum cloud-qwen3-results.tar.gz
```

使用你自己的SCP或云平台下载功能回传。这里是推理评测，不是模型训练；未完成人工回答标注前不报告ASR或安全率。

官方安装依据：[PyTorch安装说明](https://pytorch.org/get-started/locally/)、[Hugging Face固定revision下载与缓存说明](https://huggingface.co/docs/huggingface_hub/guides/download)。
