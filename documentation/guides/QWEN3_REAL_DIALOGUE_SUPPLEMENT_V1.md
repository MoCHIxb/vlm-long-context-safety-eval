# Qwen3真实逐轮补充实验：云端运行

2026-11-12。仅运行Qwen3-VL-8B-Instruct，使用原正式NF4/BF16适配器与原模型revision。原18轮用户图文保持逐条一致；每轮由目标模型真实生成并写回。无干预、不预测未来、不调用评审API。

## 1. 已处理的数据

| 项目 | 规模／设置 |
|---|---|
| 风险场景 | 80 seed × C00/C09/C10/C11 × 2图片时序 × 危险/良性配对＝1280条 |
| 普通良性 | 64 seed × 8K/B08 × 2图片时序＝128条 |
| 合计 | 1408条，每条20轮，共28160次正式生成 |
| calibration / primary / heldout | 144 / 976 / 288条，沿用原split，不混算 |
| 生成参数 | max_new_tokens=1024，贪心，repetition_penalty=1.05 |
| 闸门 | calibration内4条，80次生成；包含在正式计数中，不重复跑 |

**第1—18轮**：原用户文字与图片完全保留；去掉固定assistant和gold，不改变任务或生成新攻击。

**第19轮**：重复该轨迹第18轮的原请求。危险轨迹提供拒答后继续诱导的观察机会；实际未拒答则一致性指标不适用。

**第20轮**：危险轨迹复用同seed、同条件、同图片时序的良性配对末轮请求，观察良性恢复；其他轨迹继续复用自己的良性请求。请求重复是明确的控制操作，不声称自然或自适应用户。

分析时分开报告原18轮、扩展19—20轮及完整20轮。`label`仅标记原第18轮目标，不能当全程每轮危险性；第20轮是否真正转为良性仍须独立逐前缀判断。初始共同前缀不能因后来危险目标而提前标恶意。原C09/C10的文字关系实现及重复背景局限保留，不宣称新建严格视觉冲突数据。

冻结文件：

- `data/releases/real_dialogue_v1/panel.jsonl.gz`：已处理的1408条用户脚本，约2.7MB；云端直接读取，无需240MB原JSONL。
- `design_annotations.jsonl.gz`：原设计标签及派生关系，**不是独立真值，不进入模型**。
- `manifest.json`：全部508张图片hash、数据hash、计数与闸门ID。
- `configs/real_dialogue_supplement_qwen3_v1.json`：Qwen3模型配置、冻结原执行器hash和生成预算。

## 2. 云端同步：推荐独立worktree

原云端曾出现本地改动及分支分叉。独立worktree能保留原目录、原部署配置与旧实验，不需要reset、覆盖或stash。

```bash
cd /root/autodl-tmp/vlm-long-context-safety-eval
git -c http.version=HTTP/1.1 fetch origin
git worktree add --detach ../vlm-real-dialogue-qwen3 origin/main

# 使用原Qwen3运行过的Python及模型缓存；不重新安装或下载。
export REAL_DIALOGUE_PYTHON="$PWD/.venv-cloud/bin/python"
export HF_HOME="$PWD/.cache/huggingface"
cd ../vlm-real-dialogue-qwen3

# 只校验数据/图片并规划，不加载GPU模型。
bash scripts/real_dialogue_qwen3.sh --site cloudqwen3 --stage all
```

若原Qwen3使用的是其他Python，将 `REAL_DIALOGUE_PYTHON` 改成该环境的绝对路径，例如原目录 `.cache/venvs/rtx3090/bin/python`；若模型缓存位于其他位置，则沿用原 `HF_HOME`。不要因换目录默认新建空缓存。worktree路径已存在时直接进入该目录，不重复创建；若需更新，先确认该目录没有活动实验，再显式更新其版本，运行过程中不改代码。

本发布依赖的508张图片已由Git跟踪；校验失败会明确停止，不自动改图、换模型或降低预算。新目录只共享模型缓存/解释器，实验结果写到新目录自己的outputs。

## 3. 先闸门，再全量

确认GPU没有其他推理任务后，在新worktree执行：

```bash
# 首次4条闸门；每轮落盘并打印进度。
bash scripts/real_dialogue_qwen3.sh --site cloudqwen3 --stage gate --execute

# 查看闸门回答是否非空、连贯，检查截断与显存；再继续。
bash scripts/real_dialogue_qwen3.sh --site cloudqwen3 --stage all --execute
```

`all`顺序为gate→calibration→primary→heldout，已有闸门结果会复用。也可用 `--stage calibration`、`primary`、`heldout`分开运行，每次先验证闸门。未加 `--execute` 只规划；默认stage为gate。不会启动LLaVA、Gemma或其他模型。

普通中断后，使用**同一代码、环境、site和命令**续跑：跳过已完成轨迹，从最后完成轮次继续，不重跑已提交回答。错误导致停止时保留原错误与checkpoint，先检查，再显式重试：

```bash
bash scripts/real_dialogue_qwen3.sh --site cloudqwen3 --stage all --execute --retry-errors
```

空答不算拒答，OOM不算安全。未完成轮次不提交；空答的text、tokens等可用遥测保存在错误的`last_attempt`中，生成异常则保留其轮次/输入hash。明确重试会归档原错误。truncate原文照实保留并单列，不偷偷续写或截短输入。

## 4. 输出、评审与汇总

运行目录：`outputs/real_dialogue_supplement/rd-v1-qwen3vl8b-cloudqwen3-<fingerprint>/`。计划日志会打印实际路径。代码/环境变化会生成新指纹，不能把新目录误当原目录续跑。

| 路径 | 内容 |
|---|---|
| `manifest.json`、`runtime.json` | 模型revision、实际设备、库版本、数据与执行代码指纹 |
| `progress.json` | stage、sample、当前轮、完成数、tokens与错误状态 |
| `calibration/`、`primary/`、`heldout/` | 原逐轮checkpoint、完成结果、错误及重试档案；闸门复用calibration |
| `trajectories/*.json` | 完整用户图文＋真实助手回答，含原18轮/新增两轮边界与来源 |
| `assessment_to_fill/*.json` | 每轮独立H/R/C、安全意识、合理拒答、累计危害等空白标注；续跑不覆盖人工填写 |
| `*_technical_summary.json` | 各阶段技术完成数、截断、显存峰值及生成成本，不是安全结论 |

按REVEAL组织真实对话，MemeSafetyBench分别评价危害/拒答/完成度，LLaVAShield式保留图文及角色。下一步独立评审每个可见前缀，补充充分风险证据起点和安全意识，再计算六项行为指标；未知不置0，完整会话未来内容不泄漏到早期判断。原设计gold不是独立评审，脚本不会自动为其背书。

生成完成不等于评审完成；本入口只生成技术汇总和空白工作表，不自动调用USTC或其他API。下载时保留整个运行目录，包括manifest、checkpoint、errors和空白/已填标注，不只取末轮回答。原模型结果和旧`free_history_supplement`目录不会覆盖。

## 5. 本地验证与重建

本地已完成：1408条/28160轮计数校验、508张图片SHA校验、原执行器SHA校验；10项新测试与10项原checkpoint测试通过。plan-only全量校验通过；未加载Qwen3，云端真实可运行性仍由闸门验证。

可选重建（需已有原冻结240MB数据；云端运行无需重建）：

```powershell
.venv/Scripts/python.exe scripts/prepare_real_dialogue_supplement.py --build
```

重建后如压缩字节因zlib版本不同发生变化，必须重新冻结manifest和配置，不能将新数据混入已有运行。优先使用本次提交的gzip原字节。
