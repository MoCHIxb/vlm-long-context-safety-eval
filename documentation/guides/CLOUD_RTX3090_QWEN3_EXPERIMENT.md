# 第二台RTX3090服务器：Qwen3-VL-8B正式实验

2026-11-08。用户授权另一个Qwen模型在第二台同配置服务器运行。对应原四模型计划中的`Qwen/Qwen3-VL-8B-Instruct`，不是本地Qwen2.5-VL-7B；固定revision=`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`。新入口默认且只允许qwen3vl8b，不启动LLaVA、Gemma或Qwen2.5。

## 环境和实验设置

- RTX3090 24GB×1，Ubuntu22.04，Python3.12，PyTorch2.12.1+cu130，CUDA运行时13.0，torchvision0.27.1+cu130；与第一台云机相同的14vCPU配置，主要CPU库限8线程。
- 使用同一`requirements-cloud-rtx3090.txt`及约束文件，包含Brotli1.2.0修复；在`.cache/venvs/rtx3090`创建继承镜像Torch的环境，不修改基础镜像或驱动。
- 原冻结4864条/144种子、相同图片与抽样、Qwen3原有NF4/BF16、SDPA、固定参考历史、贪心解码及1024输出上限均保持。
- 本地只继续Qwen2.5；另一台云机继续其LLaVA/Gemma任务。各机器分别串行，不复制queue_status、lock或另一模型结果到新服务器。
- Python/Torch与本地不同，保存环境记录，不宣称跨机器回答逐字一致。24GB能否覆盖全量由GPU闸门与逐条检查确认，不能只凭显卡型号保证。

## 一次部署

在**第二台服务器**的终端运行。如果已经克隆且有正在运行的任务，不要在同一工作目录更新或再开模型；应使用这台新服务器的独立工作目录。

```bash
cd /root/autodl-tmp
source /etc/network_turbo
git clone https://github.com/MoCHIxb/vlm-long-context-safety-eval.git
cd vlm-long-context-safety-eval

PYTHON_BIN=python bash scripts/cloud_experiment_rtx3090_qwen3.sh setup
bash scripts/cloud_experiment_rtx3090_qwen3.sh prepare
bash scripts/cloud_experiment_rtx3090_qwen3.sh download
```

如果仓库已存在、没有活动任务且无本地冲突，进入该目录后用`git pull --ff-only`代替clone。`PYTHON_BIN=python`应指向云镜像的Python3.12；可以先用`python --version`确认。脚本检查不符就停止，不偷偷升级Torch或降级到CPU。

508张图片、冻结数据及分类gzip均已放入Git或冻结快照，prepare直接恢复并检查，不重新生成语段或抽样，不需要再下载图片大档案。模型权重单独按固定revision下载；缓存完整就复用。此入口不依赖Gemma许可；若HF服务要求身份或触发匿名限流，在这台服务器用自己的HF账号登录，不传入其他机器的token文件：

```bash
export HF_HOME="$PWD/.cache/huggingface"
.cache/venvs/rtx3090/bin/hf auth login
```

建议至少32GB系统内存、为单模型及安装包/结果预留60GB空闲磁盘；这是容量建议，非测得峰值。网络中断重新执行download复用缓存。若出现deployment.lock，先检查是否还有下载进程；不在活动下载时删除锁。

## 保持实验运行

若没有tmux，root用户可先运行`apt-get update && apt-get install -y tmux`。之后：

```bash
tmux new -s qwen3
bash scripts/cloud_experiment_rtx3090_qwen3.sh run
```

流程为CPU输入检查→Qwen3双色图片GPU诊断→16条资源gate→4864条formal。看到`qwen3vl8b: starting formal (4864 samples)`才表示进入正式生成。终端可能较长时间无输出，详细信息在日志。离开tmux按Ctrl+B后松开再按D，返回用`tmux attach -t qwen3`；不要Ctrl+C来离开运行。

只查看计划、不加载模型：

```bash
bash scripts/cloud_experiment_rtx3090_qwen3.sh plan
```

## 进度、断点与结果

本台机器仍通过通用控制器的状态和互斥锁保证一次只加载一个模型：

```bash
cat outputs/formal_v3_18turn_runs/queue_status.json
tail -n 20 outputs/formal_v3_18turn_runs/logs/qwen3vl8b-formal.log
```

- 模型环境：`outputs/cloud_rtx3090_qwen3_environment/`。
- 生成配置：`outputs/cloud_rtx3090_qwen3_configs/queue-qwen3vl8b.json`及对应gate/formal配置。
- 正式结果：`outputs/cloud_rtx3090_qwen3_runs/formal-v318-qwen3vl8b-ffd78bcc-ad9fe617-g1024-rtx3090-qwen3-t2121-py312/`。
- gate结果：同根目录`gate-v318-qwen3vl8b-ffd78bcc-ad9fe617-g1024-rtx3090-qwen3-t2121-py312/`，不并入formal。
- 控制器状态/锁/日志/CPU面板在`outputs/formal_v3_18turn_runs/`；它们是当前机器控制信息，不从第一台服务器拷贝覆盖。

若中断，先确认所有旧控制器/模型均已退出，再以同样run命令恢复，内部使用`--resume`跳过已保存结果。残留`serial_queue.lock`只能确认其所有者进程退出后手工移除。不要改变配置或删除缓存来绕过版本校验。

每阶段生成`technical_metrics.json`，报告失败、空答、明显重复、截断、实际token、显存和耗时；完成后不会自动启动其他模型。GPU诊断和gate通过不等于安全性标注通过。

回传结果及环境（不包括密钥或权重）：

```bash
tar -czf outputs/cloud-qwen3-rtx3090-results.tar.gz \
  outputs/cloud_rtx3090_qwen3_runs \
  outputs/cloud_rtx3090_qwen3_configs \
  outputs/cloud_rtx3090_qwen3_environment \
  outputs/formal_v3_18turn_runs/queue_status.json \
  outputs/formal_v3_18turn_runs/logs
sha256sum outputs/cloud-qwen3-rtx3090-results.tar.gz
```

模型回答的API初筛/人工抽样另行执行，不在此部署脚本中调用评审API或产出ASR。此版本只完成本地脚本、数据恢复与回归测试，第二台服务器的安装、下载及GPU闸门尚待用户执行验证。
