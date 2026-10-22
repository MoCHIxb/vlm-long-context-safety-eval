# 项目文档索引

本目录集中保存项目说明和实验报告，与`src/`中的运行代码、`scripts/`中的命令行脚本、`configs/`中的实验配置以及`data/`中的样本数据分开管理。

新对话或新成员接手项目时，首先阅读`PROJECT_HANDOFF.md`。

## 使用说明

- `guides/DATASET_DESIGN.md`：第一版预实验数据集设计；
- `guides/DATASET_DESIGN_V2.md`：当前三轨数据集结构、控制变量和使用边界；
- `guides/FORMAL_DATASET_DESIGN.md`：正式实验数据集的匹配条件、规模与解释原则；
- `guides/FORMAL_V2_DATASET_DESIGN.md`：文献规模扩展集、两层实验结构与分片运行方式；
- `guides/MODEL_EVALUATION.md`：模型选择、运行框架、历史模式与固定实验协议；
- `guides/ANNOTATION_GUIDE.md`：风险状态、输出标签、双人标注和仲裁流程；
- `guides/SOURCES.md`：SafeMT、MMDS和MMDU等数据来源说明。
- `PROJECT_HANDOFF.md`：研究目标、关键决策、当前进度、运行命令和后续任务的统一交接说明。

## 实验报告

- `reports/pilot_v1_stats.md`：第一版数据集统计；
- `reports/pilot_v2_stats.md`：当前数据集统计与轨道分布；
- `reports/smoke_qwen25vl.md`：Qwen2.5-VL最小烟雾测试；
- `reports/pilot_qwen25vl_expanded.md`：扩展预实验及早期截断问题；
- `reports/protocol_v4_readiness.md`：两种模型架构的正式实验就绪检查。
- `reports/formal_v1_stats.md`：正式实验数据集规模、平衡性、长度和条件统计。
- `reports/formal_v2_stats.md`：1,554条正式候选集的轨道、来源和长度统计；
- `reports/formal_v2_qwen_gate_report.md`：Qwen2.5-VL在扩展集上的12条实机资源闸门结果。

建议先阅读`PROJECT_HANDOFF.md`，再按需要查看正式数据设计、模型运行和标注说明。模型原始输出和待填写标注文件位于`outputs/`，该目录不提交到Git。
