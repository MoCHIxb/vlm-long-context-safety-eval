# formal_v3 原始核心与文本扩充

2026-11-06用户明确接受原始144个种子，并选择保留此前六条的原文。接受记录在`data/seeds/formal_v3_core_acceptance.json`，绑定原始哈希；六条改写未合入。该记录不冒充双人独立评分，也不代表未来模型回答已获得安全性标注。

## 当前资产

| 资产 | 路径 |
|---|---|
| 扩展种子库，含中性近义文本 | `data/seeds/formal_v3_extended_seed_bank.json` |
| 4224条完整轨迹 | `data/processed/formal_v3_extended.jsonl` |
| 四类风险与良性层共5个压缩分片 | `data/processed/formal_v3_extended_shards/` |
| 数据配置 | `configs/formal_v3_extended.json` |
| 构建事实、哈希与限制 | `documentation/reports/formal_v3_extensions_status.json` |
| 生成请求、响应及阶段记录 | `outputs/formal_v3_original_core_extensions/` |

规模仍为80风险种子和64良性种子，144个独立来源场景、4224条控制轨迹。近义块或条件变体不计作新增独立场景。生成器`deepseek-flash-2`仅为辅助作者，不是四模型评测对象。

## 构造规则

原始五个风险核心atom及良性请求保持原文。80个风险种子各有一份C09/C10/C11，共240段；依据现有文字描述生成，不向API发送图片，因此不能据此声称新图文操纵已逐图核验。

144个种子各有12块原中性开场的近义扩充，共1728块。按同一种子固定顺序、完整句循环填充，各条件不单独随机生成；静态/动态与安全/危险共享相同历史。更长档沿用相同近义句序列，不改变最终请求，不以新增风险步骤扩充内容。

为建立统一的最短档参考历史，54个良性种子的可选来源助手历史按完整句缩短一次，并用于该种子的所有长度版本；原始用户请求保留。长度目标仍沿用空白词数除以0.75的构建估算，最大估算偏差约4.10%。这不等于四模型实际输入token，正式推理前必须另测图像和聊天模板开销。

## 重建

从发布种子库重建，无须API、模型权重或GPU；需要已提取的原始图片：

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts/build_formal_v3_extensions.py --embedded
```

原始核心哈希匹配检查与无网络预检查：

```powershell
.\.venv\Scripts\python.exe scripts/generate_formal_v3_extensions.py --dry-run
```

有必要继续API生成时，使用既有加密凭据：

```powershell
.\scripts\invoke_ustc_api.ps1 -Action original-core-extensions
```

已有成功候选直接复用，历史失败不自动重复收费调用。原始种子变更后不会自动继承旧接受结论。

## 审校归档

旧A/B、阅读稿、译文、审校工具及废弃修订版本共633个文件已在ZIP完整校验后移出工作目录，种子审校流程已关闭。归档在`archives/formal_v3_review_workflow_20261106.zip`，恢复时按项目相对路径解压。归档为本地文件，不纳入普通Git提交；迁移项目时如需保留历史审校细节，应同时复制此ZIP。

原始数据、当前接受记录、扩充输出、模型部署和未来模型回答标注功能均保留。新的扩充语段记为API生成、结构校验后按用户指令整合，不伪造逐段人工评分。当前没有真实模型安全率或ASR结果。
