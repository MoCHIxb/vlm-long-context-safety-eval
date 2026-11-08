# 长上下文多轮VLM安全数据集

本仓库当前用于重新构造毕业设计第一阶段的核心受控数据集，研究以下输入因素对视觉语言模型安全应答的影响：

- 视觉证据静态呈现或动态进入历史；
- 上下文长度；
- 对话轮数；
- 风险位置与分布；
- 图文关系；
- 用户意图轨迹；
- 风险类别；
- 安全/危险最终目标。

模型类型不是数据集因素。数据冻结后，不同模型运行同一测试面板，仅用于外部对照。

## 数据版本

- `pilot_v1`：192条早期静态原型；
- `pilot_v2`：160条静态、动态和良性预实验数据；
- `formal_v1`：456条旧核心受控数据；
- `formal_v2`：1,554条旧正式候选数据，其中核心受控层独立种子不足；
- `formal_v3`：保留的机器构造基线，共144个独立场景、4,224条轨迹；2026-11-06用户决定接受全部原始种子，六条改写不合入。
- `formal_v3_extended`：基于原始种子补充240段C09/C10/C11，并使用144份中性近义文本库扩充上下文；当前状态见`documentation/reports/formal_v3_extensions_status.json`。
- **当前协议 `formal_v3_18turn`**：18轮基准，比较6/12/18/24/30轮；使用可重放的随机中性文本计划，共144个种子、4864条轨迹。旧版本均保留，不混用其条件编号或运行结果。

`formal_v3`不覆盖旧版本。详细方案见[FORMAL_V3_DATASET_DESIGN.md](documentation/guides/FORMAL_V3_DATASET_DESIGN.md)。

## 当前18轮协议规模

```text
80个风险种子 × 14个条件 × 2种视觉时序 × 2种标签 = 4,480
64个良性种子 × 3种长度 × 2种视觉时序（固定18轮）= 384
合计：4,864条轨迹，144个独立语义种子
```

静态与动态版本使用完全相同的图片集合和对话文本，只改变图片进入历史的轮次：

- `static_initial_bundle`：全部图片在第一轮一次出现；
- `dynamic_incremental`：同一图片集合按轮次逐步出现。

## 当前目录

```text
configs/                  数据构建配置
data/seeds/               来源种子与formal_v3种子规范
data/raw/                 可复现下载的来源元数据和图片
data/processed/           已生成的数据版本
data/derived/             API扩充文本与整合中间结果
archives/                 本地可恢复的历史审校归档（不提交Git）
documentation/guides/     数据设计与来源说明
documentation/reports/    数据统计和构建状态
scripts/                  下载、构建、验证和统计脚本
tests/                    数据结构测试
```

## 当前工作入口

1. 阅读`documentation/PROJECT_HANDOFF.md`；
2. 阅读`documentation/guides/FORMAL_V3_18TURN_PROTOCOL.md`；
3. 查看`configs/formal_v3_18turn.json`及其来源种子库`data/seeds/formal_v3_extended_seed_bank.json`；
4. 核对`data/processed/formal_v3_18turn_shards/manifest.json`、构建报告和独立验证报告；
5. 本地仅继续当前Qwen2.5-VL-7B，完成后暂停并检查；其余模型不在本地自动接续。状态见`outputs/formal_v3_18turn_runs/queue_status.json`，勿重复启动第二个队列。

## 云服务器运行

第二台同配置RTX3090可使用独立Qwen3-VL-8B入口`bash scripts/cloud_experiment_rtx3090_qwen3.sh setup/prepare/download/run`（四个action分别执行），默认只跑Qwen3；详见[CLOUD_RTX3090_QWEN3_EXPERIMENT.md](documentation/guides/CLOUD_RTX3090_QWEN3_EXPERIMENT.md)。LLaVA/Gemma仍使用原RTX3090入口，每台机器各运行一个模型。

已提供Linux/RTX4090部署入口，默认云端Qwen3-VL-8B，与本地Qwen2.5-VL-7B分工。保持相同数据、固定模型revision、NF4/BF16和1024输出预算；详情见[CLOUD_EXPERIMENT.md](documentation/guides/CLOUD_EXPERIMENT.md)。

```bash
PYTHON_BIN=python3.14 bash scripts/cloud_experiment.sh setup
bash scripts/cloud_experiment.sh prepare
bash scripts/cloud_experiment.sh download --model qwen3vl8b
bash scripts/cloud_experiment.sh run --model qwen3vl8b
```

Git包含代码、配置、来源种子、固定压缩数据快照及当前实验所需508张原始图片；图片路径、来源和SHA-256保持不变。模型权重仍单独下载，凭据、缓存及实验回答不上传。prepare直接恢复冻结压缩分片，避免跨Python/zlib环境重新压缩产生不同校验值；图片已存在且校验通过时不联网下载。

原始144个种子的接受结论绑定原文件哈希，保存在独立记录中；不把API生成或机器校验写成双人评分。旧审校材料与工具在扩充构建成功后归档清理，见`documentation/reports/formal_v3_review_archive.json`。原始构造文件保留历史状态，不覆盖。

API原始扩充入口为`scripts/generate_formal_v3_extensions.py`，旧整合入口为`scripts/build_formal_v3_extensions.py`。当前18轮构建与独立校验入口为`scripts/build_formal_v3_18turn.py`、`scripts/validate_formal_v3_18turn.py`。随机性在构建时固定，配对及跨模型复用同一结果；开场与最终请求不覆盖、不补词。

四模型权重已在本地准备；本地当前只继续Qwen2.5-VL，完成后暂停，云端默认另跑Qwen3-VL。每模型先做16条输入/资源检查，通过后进入4864条正式运行；每台服务器单次只加载一个模型。输入检查只覆盖资源闸门面板，全量每次生成仍会检查上下文上限并记录真实token；不能将名义2K/8K/16K视为跨模型精确等长。历史部署说明见[OPEN_MODEL_DEPLOYMENT.md](documentation/guides/OPEN_MODEL_DEPLOYMENT.md)，最新云端步骤见上述云服务器指南。

## 数据使用边界

- 数据仅用于经过授权的模型安全研究和评测；
- 不应将危险样本用于现实操作、部署或传播；
- 所有图片必须保留来源、许可和哈希；
- 数据划分以`seed_id`为单位，禁止同一种子的条件变体跨集合泄漏；
- JSONL轨迹数不能当作独立场景数；
- 未经双人审校的构造标签不能当作真实风险分数。
