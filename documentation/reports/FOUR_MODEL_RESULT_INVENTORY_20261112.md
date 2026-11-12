# 四模型正式输出统一整理（2026-11-12）

范围：原formal_v3_18turn固定参考历史实验，4864条/模型、144种子。只整理原输出，不包括资源闸门、逐轮真实生成补测或干预实验；没有启动GPU或新增API判定。

## 核验结果

| 模型 | 已获得输出 | 技术失败样本 | 保留错误记录 | 无解释缺失 | 达到1024输出上限 | 上限比例 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen2.5-VL-7B | 4864 | 0 | 0 | 0 | 212 | 4.36% |
| Qwen3-VL-8B | 4864 | 0 | 0 | 0 | 514 | 10.57% |
| LLaVA-OneVision-7B | 4864 | 0 | 0 | 0 | 2 | 0.04% |
| Gemma3-12B-IT | 4863 | 1 | 2 | 0 | 2587 | 53.20% |

总计划19456个模型×样本单元，19455个有输出，1个技术失败。四模型共同有输出的样本4863条。四模型均0空答、0高重复启发式标记，但不等于模型正确或安全。

新增确认语回声标记（最终模型文本strip/casefold后与最后一条固定参考assistant相同）：Qwen2.5为205、Qwen3为2809、LLaVA为3028、Gemma为606条。它们是真实生成的短回答，不属于空答或高重复长文，原输出全部保留；不能单凭无技术错误就宣称有效任务完成或稳健安全拒绝。Qwen3完成评审的核查见`QWEN3VL8B_MACHINE_FINDINGS_20261112.md`。

Gemma=原运行4682＋补跑181；补跑的模型配置、数据、原图、实现、生成参数、历史模式均与原运行一致，配置差异仅run_id/sample_ids/recovery_note。原run_id/provenance保留，不把新文件搬进旧目录。单样本独立重试仍OOM：`V318-V3B-034-B16-static_initial_bundle-safe`。两份不同运行错误正文/堆栈均保留，按1个失败样本统计；它们不是2个独立实验样本，也不代表总共只重试2次。

按用户决定保留报错作为实验技术误差，不作为安全拒绝或不安全配合。该OOM已多次复现，不能声称已证明随机缺失、纯偶然或统计无偏。所有安全分析须单列技术失败和有效分母；完整案例交叉比较使用4863条时，也保留原4864计划及排除原因。

Gemma截断比例较高，是需要单独分析的输出预算现象，不并入这1个OOM，也不直接计为安全/不安全。后续评审应对截断进行标记和敏感性分析，不自动补写或重跑截断回答。

## 输入与技术指标

| 模型 | 最大实际输入tokens | Torch分配峰值/GiB | 成功样本累计生成小时 |
|---|---:|---:|---:|
| Qwen2.5-VL-7B | 27091 | 10.63 | 32.81 |
| Qwen3-VL-8B | 27080 | 12.48 | 21.91 |
| LLaVA-OneVision-7B | 28855 | 10.99 | 6.48 |
| Gemma3-12B-IT | 26828 | 22.42 | 101.71 |

时长是已保存成功回答的duration_seconds之和，不含下载、权重加载、闸门、关机等待或失败尝试。显存是PyTorch分配峰值，不是整卡峰值。硬件/运行库不同、回答长度也不同，不能直接当统一硬件的速度排名。

## 归档校验

- `data/releases/cloud_rtx3090_llava_gemma_20261112T044919Z_results.tar.gz`：11047411字节，SHA-256=`580272df46ebd07a4f860ea883f9a260d2ed88117937c197bcf12d5f3b19cd16`，9799个归档文件与隔离导入逐份hash一致。
- Qwen3原归档SHA-256=`8f74944013ff8c8cd8413f25fbb4f25f86fed7fb29193155b12d02b1a8047950`，4896个文件与已有导入逐份hash一致。
- 新包导入`outputs/cloud_imports/llava-gemma-20261112T044919Z/`，没有覆盖本地queue_status、锁、模型结果或API评审文件。
- `.ipynb_checkpoints`保留在原归档/隔离导入中，但不当正式样本计数；LLaVA真正的根目录正式结果是4864条。
- 统一索引逐条验证样本ID、元数据/每轮结构、来源manifest/configuration hash、冻结数据与实现hash、固定参考历史、生成参数；共19469份结果/配置/manifest/错误源文件在整理结束前重新核验未变。

## 统一数据组织

本地入口`outputs/unified_formal_v3_18turn/latest.json`指向最新已核验快照；无summary或无latest引用的中间目录不作为正式入口。运行`scripts/organize_four_model_results.py`会生成新快照而非覆盖旧快照，不调用任何模型/API。

```text
快照/
  README.md                         总览与解释边界
  summary.json                      四模型计数、截断、技术指标
  records/{model_key}.jsonl          每模型4864行完整结果信封
  models/{model_key}.jsonl           每模型4864行轻量索引及技术标记
  sample_matrix.jsonl               4864行，按sample_id对齐四模型
  common_four_model_sample_ids.json  4863个共同有输出的ID
  coverage_by_group.json            按split/条件/目标/时序的覆盖统计
  errors/all_preserved_error_records.jsonl
  errors/originals/                 两份原错误JSON的原字节副本
  source_runs.json                  原运行与补跑来源
  source_files_sha256.json          源文件hash清单
```

model_key为qwen25vl7b/qwen3vl8b/llava7b/gemma3_12b。完整结果信封中的`result`保留原字典（含run/provenance），技术失败行`result=null`，不伪造回答；`source_path/source_sha256`指向原文件及其原字节hash。用户脚本仍由共享冻结dataset定位，未将同一份大数据集重复拷贝四次。

发布包`data/releases/formal_v3_four_model_outputs_20261112.zip`内`four_model_fixed_reference/`包含上述统一输出及校验回执，方便独立读取四份records JSONL；原LLaVA/Gemma归档也单独保留。实际发布状态以Git提交及推送核验为准，不从文件存在推断已经上传。

## 分析边界

此次不新增安全标签，不修改既有Qwen2.5/Qwen3评审或其正在进行的任务。LLaVA/Gemma还需要按统一且已校准的协议评审。模型输出失败、API评审失败、意图冲突和输出截断属于不同层面，不能混为一个“错误率”或统一当作安全回答。当前整理结果也不能替代人工抽样审核。
