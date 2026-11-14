# LLaVA与Gemma：同一1408条真实多轮补充实验

2026-11-14。新入口 `scripts/real_dialogue_models.sh`，必须指定 `--model llava7b` 或 `--model gemma3_12b`，一次只运行一个模型。原Qwen3脚本、配置和实现未修改，保留其断点指纹。

本次复用Qwen3已经冻结的同一批用户图文：1408条×20轮＝28160次/模型。4条gate/80次调用包含在calibration中，后续复用。第1—18轮保留原用户图文，第19轮重复原目标，第20轮危险组转为良性配对请求；原18轮与新增两轮分开统计。共享数据包的名称含qwen3只表示最初发布来源，不是执行模型身份。

## 同步与环境

推荐独立worktree，保留旧云目录的分叉、部署配置和LLaVA错误checkpoint：

```bash
cd /root/autodl-tmp/vlm-long-context-safety-eval
git -c http.version=HTTP/1.1 fetch origin
git worktree add --detach ../vlm-real-dialogue-lg origin/main
export REAL_DIALOGUE_PYTHON="$PWD/.cache/venvs/rtx3090/bin/python"
export HF_HOME="$PWD/.cache/huggingface"
cd ../vlm-real-dialogue-lg
```

若worktree已存在，直接进入对应目录；不要覆盖活动运行。若原环境/缓存位于别处，将上述路径改成原LLaVA/Gemma实际使用的位置。两种模型均使用原正式NF4/BF16配置和固定revision，不重新安装、下载或自动切换。先确认GPU没有其他推理进程，两个模型串行执行。

## LLaVA：先校验、再闸门、后全量

```bash
# 只校验和规划，不加载模型。
bash scripts/real_dialogue_models.sh --model llava7b --site cloud3090llava --stage all

# 先运行4条闸门。
bash scripts/real_dialogue_models.sh --model llava7b --site cloud3090llava --stage gate --execute

# 检查回答正常、脚本连贯，再运行全量。
bash scripts/real_dialogue_models.sh --model llava7b --site cloud3090llava --stage all --execute
```

## Gemma：待LLaVA进程退出后执行

```bash
bash scripts/real_dialogue_models.sh --model gemma3_12b --site cloud3090gemma --stage all
bash scripts/real_dialogue_models.sh --model gemma3_12b --site cloud3090gemma --stage gate --execute
bash scripts/real_dialogue_models.sh --model gemma3_12b --site cloud3090gemma --stage all --execute
```

Gemma沿用正式配置的 `do_pan_and_scan=false`。不因新轨迹OOM自动压缩、裁图、缩短历史或换模型；旧单样本OOM决定和原结果保持不变。

## 中断、错误与输出

- 普通中断：同一代码/环境/site下重复原命令，自动复用已保存轮次与完成轨迹。
- 遇到保存的错误：先检查，需重试时在原命令末尾加 `--retry-errors`；原错误归档，未完成轮次不伪造。
- LLaVA以前发生过EOS-only空答，新数据仍保留原重复背景，因此该问题可能再次出现。空答默认停止，不当拒答；错误文件保存 `last_attempt` 的轮次、输入hash、回答及tokens，不承诺已修复空答原因。
- 输出：`outputs/real_dialogue_supplement/rd-v1-<model>-<site>-<fingerprint>/`，含progress、完整轨迹、逐轮checkpoint、技术摘要和不覆盖的空白评审表。
- 原 `free_history_supplement.sh` 是另一套1600条、6—30轮实验，不能混作本次20轮结果；旧LLaVA checkpoint也不能接到本次新协议。
- 不自动调用评审API，不加载SAPT或风险模型。无干预真实输出收集完成后再独立逐轮评审。

验证：两模型全量plan、5项模型路由/状态/断点测试、10项原补充实验测试及Bash语法检查通过；Qwen3原运行指纹保持一致。不代表两种模型已通过真实GPU闸门。详细数据和评价口径沿用 `QWEN3_REAL_DIALOGUE_SUPPLEMENT_V1.md`。
