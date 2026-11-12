# 逐轮真实回答：轮数补测v1

本补测复用冻结formal_v3_18turn中的用户文字和原始图片，但所有轮次的assistant内容都由待测模型生成，完整带入下一轮。不会插入原assistant_context/Noted.参考回复；如果模型自己生成Noted.，仍按真实输出保存。用户问题预先固定，不会根据模型回答自适应改写，因此准确称为“固定用户脚本下的逐轮生成”，不等于自主攻击者对话。

## 范围与预算

协议：`configs/free_history_supplement_v1.json`。

| 项目 | 设置 |
|---|---|
| 轮数 | 6、12、18、24、30（C01/C02/C00/C12/C13） |
| 种子 | 全部80个风险种子，沿用calibration/primary/heldout划分 |
| 视觉呈现 | 静态/动态均保留 |
| 最终目标 | 危险/匹配安全均保留 |
| 每模型正式轨迹 | 80×5×2×2=1600 |
| 每模型正式生成调用 | 28,800（不是1600次单轮生成） |
| 每轮生成参数 | greedy、repetition_penalty=1.05、max_new_tokens=1024，历史轮与最终轮相同 |
| 资源闸门 | 同一个calibration种子，6轮/30轮、静态/动态及两种目标共4条，额外72次调用 |
| 普通良性B层 | 当前没有轮数全交叉，不擅自将384条长度面板混入轮数补测 |

四模型正式合计6400轨迹、115200次生成，另有闸门开销。实际回答会增加后续输入长度，计算量不能按旧实验每条最终回答的速度直接估计。长轨迹可能超过上下文限制或显存，原适配器会报错，不裁剪历史。1024是原运行预算，不保证每个历史回答自然结束；历史/最终截断分别记录，截断文本原样带入后续轮，分析需报告其影响。

现有适配器每轮重新处理累计的完整历史，不在多次generate调用之间复用KV缓存；因此会多次进行prefill。这不会丢失历史，但会增加运行时间，不能按流式聊天服务的速度估算。

这是一项独立协议，输出不与旧fixed_reference结果混用。原用户文本的名义长度保持不变，真实模型历史长度会随轮数和模型变化，不能把结果直接解释为“实际总token完全相同条件下的纯轮数因果效应”。固定历史实验保留作参照。模型类型仍只作外部对照，不是数据集受控因素。

## 本地Windows

复用原`.venv`、本地HF缓存和模型授权，无需重装环境。先确认原GPU模型任务已经结束；API评审不等于模型GPU运行，但也不要误停止其他任务。

```powershell
cd 'D:\papers\Graduation Project\vlm-long-context-safety-eval'

# 只验证数据/图片/代码与生成计划，不加载模型，不使用GPU
.\scripts\free_history_supplement.ps1 -Model qwen25vl7b -Site local5070ti

# 明确执行：先4条闸门，再同一模型1600条正式轨迹
.\scripts\free_history_supplement.ps1 -Model qwen25vl7b -Site local5070ti -Execute
```

## 云端Linux / RTX3090

先拉取已发布代码，保留原云端模型设置、结果和加密/登录缓存；若git提示本地修改冲突，不用reset/clean强行覆盖。模型权重和冻结图片已部署的实例无需重新下载。

```bash
cd /root/autodl-tmp/vlm-long-context-safety-eval
git pull --ff-only

# 只准备，无GPU
bash scripts/free_history_supplement.sh --model qwen3vl8b --site cloud3090qwen3

# 在tmux中运行；确保该卡原模型任务已结束
bash scripts/free_history_supplement.sh --model qwen3vl8b --site cloud3090qwen3 --execute
```

LLaVA/Gemma服务器只需替换模型和site，例如`--model llava7b --site cloud3090a`。允许本地Qwen与另一台云服务器同时运行；同一张GPU不并行加载两个模型。同一checkout的补测采用OS文件锁；另检测旧formal串行队列锁，存在时拒绝加载而不是自动停止旧任务。独立checkout之间不能依赖该锁，仍需检查GPU。

Gemma已经出现的长输入OOM不因本协议自动解决，30轮自由回答可能进一步提高资源需求。先看闸门结果，不静默切换卸载、图片分辨率或生成预算。

## 进度、结果与逐轮续跑

启动时打印唯一目录：

```text
outputs/free_history_supplement/fh-v1-模型-site-指纹/
  manifest.json          # 协议、冻结数据/图片/实现SHA、模型配置、环境身份
  panel.json             # 1600条ID、4条gate ID及预期调用数，计划不是执行凭证
  runtime.json           # 实际模型类、设备映射、版本；续跑必须一致
  progress.json          # 当前阶段、样本、轮次、已提交调用数
  gate/
  formal/
    V318-*.json          # 完整轨迹，每轮response.source均为model
    checkpoints/        # 每轮原子保存的最后完整回答，可在轨迹中间恢复
    errors/             # 故障单列，不当安全/拒绝
    error_history/      # 显式重试前保留旧故障
    technical_summary.json
```

原始正式结果目录不会被写入。本协议只做推理和技术汇总，不发API评审请求，不生成ASR/安全率结论。四条闸门仅验证资源和接口，不证明数据/回答已人工通过，也不覆盖全部场景。默认`--stage all`；`--stage gate`只做闸门，`--stage formal`仍先验证/完成闸门。已经完成的闸门和轨迹不会重跑。

停止可用Ctrl+C，已写入的每轮回答保留；断电后OS锁自动释放，残留锁文件本身不是占用证据。相同命令恢复时核对checkpoint内容hash、源记录、模型/环境身份和每轮真实输入历史；只重新生成尚未完整写入的那一轮，不从Noted.重建历史。

发生OOM、空回答或上下文超限，默认停止。保存失败后必须明确加重试参数：

```powershell
.\scripts\free_history_supplement.ps1 -Model qwen25vl7b -Site local5070ti -Execute -RetryErrors
```

```bash
bash scripts/free_history_supplement.sh --model qwen3vl8b --site cloud3090qwen3 --execute --retry-errors
```

不自动重试同一技术错误；先诊断原因。仅修改site标签不能解决显存不足。不同机器用不同site，site相同但包版本/执行环境/代码变化也会产生不同指纹目录，不得手工合并冒充同一运行。部署脚本本身变化不写进旧结果。

## 分析与校验重点

- 每轮均保存真实文本、输入/输出tokens、截断、耗时和显存；不只保留最终轮。控制台不打印回答原文。
- `history_before_user_sha256`记录输入当前用户轮之前的真实前缀；`input_history_sha256`记录加上当前用户轮的模型可见历史（图片用相对路径标识）。相同用户前缀不保证模型前缀一致，技术汇总报告安全/危险目标配对中真实前缀一致的数量。
- 不能把不同模型生成的不同历史视为相同实际输入，模型间比较是各自完整对话轨迹的外部对照。
- 新增样本要单独校准逐轮评审：最终安全性、首次有害帮助轮次、拒绝后是否转为配合、良性完成、累计tokens等可作为后续分析。旧评审器的“只看最终模型输出、历史固定参考”假设不能直接照搬。当前脚本不提前计算这些安全指标。
- 不从生成数量、技术闸门通过或无OOM推断模型安全；也不将中断轨迹计为安全轨迹。对比旧fixed_reference时按相同seed/条件/时序/目标对齐，并分开报告实际上下文长度及历史截断。

验证：`python -m unittest discover -s tests -p test_free_history_supplement.py -v`。测试用状态化假模型检查实际回答进入下一轮、逐轮中断恢复、篡改拒绝、空答停止、截断保留、锁及闸门失败不推进正式阶段；测试不是四模型GPU运行的替代品。
