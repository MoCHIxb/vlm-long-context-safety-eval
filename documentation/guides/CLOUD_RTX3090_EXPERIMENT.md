# RTX3090：LLaVA-OneVision-7B与Gemma 3 12B

这是独立新增的部署方案。旧`cloud_experiment.sh`、`cloud_runtime.py`、依赖文件、RTX4090指南和冻结的模型/数据/运行配置保持原样。本地Qwen继续当前运行，完成后暂停；本方案不启动Qwen模型。

## 目标环境和工作量

- Ubuntu22.04、Python3.12、PyTorch2.12.1、PyTorch CUDA运行时13.0。
- 单张RTX3090 24GB；14 vCPU Xeon Gold6330。脚本默认将主要CPU计算库限制为8线程，避免多个库各开14线程争抢；这不是已测得的最优值。
- torchvision0.27.1，与PyTorch2.12.1/CUDA13.0的官方版本组合一致：[PyTorch版本表](https://pytorch.org/get-started/previous-versions/#v2121)。
- 推理包继续使用已有`requirements-cloud.txt`的版本，新文件`requirements-cloud-rtx3090.txt`叠加Torch版本约束。与本地Torch2.14.1/Python3.14存在环境差异，必须分别记录，不能宣称跨平台输出逐字一致。
- 先LLaVA-OneVision-7B，再Gemma 3 12B IT，各16条资源闸门、各4864条正式结果，共9728条正式结果。NF4/BF16、固定参考历史、1024输出预算、同一数据和模型revision均保留。
- 24GB显存是否能完成全部长输入由资源闸门及逐条检查确定，不提前宣称通过。建议系统内存32GB以上，为两个模型、安装包和结果预留100GB磁盘；这些是容量预留建议，非本实验实测峰值。

## 1. 获取新增脚本

新服务器：

```bash
git clone https://github.com/MoCHIxb/vlm-long-context-safety-eval.git
cd vlm-long-context-safety-eval
```

已经克隆则在确认没有本地修改后执行`git pull --ff-only`。不要在有活动实验的同一个目录更换代码。

## 2. 安装独立环境

先进入云平台提供的Python3.12环境，确认它能导入预装PyTorch：

```bash
python --version
python -c "import torch; print(torch.__version__, torch.version.cuda)"
nvidia-smi
PYTHON_BIN=python bash scripts/cloud_experiment_rtx3090.sh setup
```

如果镜像命令名是`python3`，将`PYTHON_BIN`改为`python3`。setup先检查实际Python3.12、Torch2.12.1和torch.version.cuda=13.0，再创建`.cache/venvs/rtx3090`，以`--system-site-packages`方式复用镜像的PyTorch；新增包安装进此独立环境，不重装基础环境，也不自动更新驱动。pip约束阻止静默升级Torch；torchvision使用CUDA13.0官方wheel。重复执行会复用同一虚拟环境。

安装后验证模型类可导入、CUDA可用、BF16实际矩阵运算、GPU型号/容量及主要包版本。环境不符会停止，保留错误供排查。若安装时提示某个包缺少Python3.12 wheel或依赖冲突，请保留日志，不要自行去掉版本约束后混用结果。Linux镜像安装、模型下载和真实GPU闸门必须在服务器完成，本地开发验证不等于它们已经通过。

## 3. 准备数据与HF授权

```bash
bash scripts/cloud_experiment_rtx3090.sh prepare
export HF_HOME="$PWD/.cache/huggingface"
.cache/venvs/rtx3090/bin/hf auth login
```

Gemma需要在HF获批的账号登录这台服务器；本机HF授权凭据不会随Git同步。请在服务器交互式输入凭据，不要放进聊天或代码。prepare复用原有冻结快照恢复和508张图片校验，不改动数据、不调用生成API。

## 4. 下载两个模型

```bash
bash scripts/cloud_experiment_rtx3090.sh download --include-gated
```

默认下载并检查LLaVA和Gemma的固定revision。Gemma授权未完成时，可以先只准备LLaVA：

```bash
bash scripts/cloud_experiment_rtx3090.sh download --model llava7b
```

## 5. 运行与恢复

```bash
# 仅生成和查看计划，不加载模型。
bash scripts/cloud_experiment_rtx3090.sh plan

# 推荐在tmux内保持任务运行。
tmux new -s vlm3090
bash scripts/cloud_experiment_rtx3090.sh run
```

按LLaVA→Gemma顺序串行，CPU输入检查→双色GPU诊断→16条gate→4864条formal。任一阶段出错、不完整或明显系统性退化会停止后续；截断单独统计。只跑LLaVA时可用`run --model llava7b`；只跑Gemma时可用`run --model gemma3_12b`。选择两个模型的顺序以命令顺序为准，默认即先LLaVA。

中断后确认旧进程退出，以相同命令重启，内部使用`--resume`。若留下锁，先核对其中PID已退出，才可手动移除。新旧云端入口共用同一目录的串行队列锁，防止同时加载两个模型。若旧4090控制器仍在同一目录运行，不要启动这个入口。

## 6. 结果位置

本方案使用独立的配置及run_id，避免与旧云端结果混合：

```text
outputs/cloud_rtx3090_environment/       Python、Torch、CUDA、GPU及包版本
outputs/cloud_rtx3090_configs/           本方案生成的gate/formal/queue配置
outputs/cloud_rtx3090_runs/
  gate-v318-llava7b-ffd78bcc-ad9fe617-g1024-rtx3090-t2121-py312/
  formal-v318-llava7b-ffd78bcc-ad9fe617-g1024-rtx3090-t2121-py312/
  gate-v318-gemma3_12b-ffd78bcc-ad9fe617-g1024-rtx3090-t2121-py312/
  formal-v318-gemma3_12b-ffd78bcc-ad9fe617-g1024-rtx3090-t2121-py312/
```

控制器仍复用`outputs/formal_v3_18turn_runs/queue_status.json`、`logs/`与`serial_queue.lock`；CPU输入面板报告仍写在该目录`preflight/`。这是同台机器的控制状态，并不把正式结果写回旧run目录。每阶段的`technical_metrics.json`保存在对应gate/formal目录。

回传时打包结果、配置、环境、状态和日志，不包含HF缓存和凭据：

```bash
tar -czf outputs/cloud-rtx3090-results.tar.gz \
  outputs/cloud_rtx3090_runs outputs/cloud_rtx3090_configs \
  outputs/cloud_rtx3090_environment \
  outputs/formal_v3_18turn_runs/queue_status.json \
  outputs/formal_v3_18turn_runs/logs
sha256sum outputs/cloud-rtx3090-results.tar.gz
```

截断、失败、耗时和显存是技术指标；模型回答经评价之前，不报告安全率或ASR。


## config.json下载出现TypeError时

若环境检查通过但只看到`llava7b: TypeError`，还不能判定根因。更新代码后在云端执行小文件诊断（不下载权重、不加载GPU）：

```bash
git pull --ff-only
.cache/venvs/rtx3090/bin/python scripts/diagnose_hf_download.py --model llava7b
# 若仍失败，可对照关闭进度条的结果。
.cache/venvs/rtx3090/bin/python scripts/diagnose_hf_download.py --model llava7b --disable-progress
```

输出包含脱敏后的错误类型、message、frames和异常链HTTP状态，不输出令牌或完整请求URL。请回传这些诊断输出后再决定修改依赖或网络设置；不要先重装Torch、清空权重缓存或更改实验配置。
