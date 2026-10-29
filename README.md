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
- `formal_v3`：已完成机器构造与结构验证，共144个独立场景、4,224条轨迹；人工双人审校尚未完成。

`formal_v3`不覆盖旧版本。详细方案见[FORMAL_V3_DATASET_DESIGN.md](documentation/guides/FORMAL_V3_DATASET_DESIGN.md)。

## `formal_v3`目标规模

```text
80个危险种子 × 12个条件 × 2种视觉时序 × 2种标签 = 3,840
64个良性种子 × 3种长度 × 2种视觉时序 = 384
合计：4,224条轨迹，144个独立语义种子
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
data/review/              formal_v3双人种子审校文件
documentation/guides/     数据设计与来源说明
documentation/reports/    数据统计和构建状态
scripts/                  下载、构建、验证和统计脚本
tests/                    数据结构测试
```

## 当前工作入口

1. 阅读`documentation/PROJECT_HANDOFF.md`；
2. 阅读`documentation/guides/FORMAL_V3_DATASET_DESIGN.md`；
3. 查看`configs/formal_v3.json`和`data/seeds/formal_v3_seed_template.json`；
4. 查看`data/processed/formal_v3_shards/manifest.json`和`documentation/reports/formal_v3_stats.md`；
5. 在模型实验前完成144个种子的人工双人审校。

模型运行配置和旧模型输出已经清理。当前数据哈希已经生成；新的模型实验只能在人工审校完成并冻结审定版哈希后重新建立。

## 数据使用边界

- 数据仅用于经过授权的模型安全研究和评测；
- 不应将危险样本用于现实操作、部署或传播；
- 所有图片必须保留来源、许可和哈希；
- 数据划分以`seed_id`为单位，禁止同一种子的条件变体跨集合泄漏；
- JSONL轨迹数不能当作独立场景数；
- 未经双人审校的构造标签不能当作真实风险分数。
