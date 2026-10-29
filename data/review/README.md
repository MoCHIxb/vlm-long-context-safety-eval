# `formal_v3` 人工种子审校

`formal_v3_seed_review_reviewer_a.jsonl`和`formal_v3_seed_review_reviewer_b.jsonl`包含相同的144个种子，但顺序不同。两名审校者应独立填写`review`字段，不得先查看对方结果。

`decision`建议使用`accept`、`revise`或`reject`。所有布尔字段应明确填写；`revise`和`reject`必须给出`revision_notes`。完成后再编写合并与分歧仲裁脚本，不能由构建程序自动把空白审校项填为通过。

## 英文原文阅读JSON（2026-10-29更新）

当前阅读文件是`formal_v3_readable_original_en.json`，包含全部144个种子，采用两空格缩进，按场景展开。用户自行处理评价填写；阅读文件不包含评价填写字段。

- 顶层`records`数组按种子编号排列，80个风险场景、64个良性场景。
- 良性场景的`dialogue_outline`按轮次列出英文原文，`final_request`保留最终请求；风险场景使用原始`dialogue_atoms`字段。
- `topic`、原始分类、数据划分与来源编号均保留。除图片占位符替换外，题干文字不变。
- `source_images`提供623个原始来源图片链接，并保留`source_image_number`与`included_in_experiment_evidence`。
- 406处显式编号图片占位符已经替换为本机文件URL，无未解析占位符。可在支持链接的编辑器中Ctrl+单击或复制URL打开。
- `experiment_evidence_packets`单独列出正式实验选用的图片；完整来源图用于阅读核对，不会改变正式实验的证据选择。

当前文件不含译文。此前全部翻译文件、翻译脚本、Excel、预览图、检查记录和独立Markdown阅读稿均已清理。原始种子库、正式数据与两份A/B审校JSONL保留。

构建命令：`.venv/Scripts/python.exe scripts/prepare_formal_v3_readable_original.py`。该脚本只格式化原文、替换图片占位符并校验链接，不调用模型或网络服务。

链接为当前项目绝对位置的`file:`URL，移动项目目录后需要重建阅读文件。原始图片编号与当前证据包编号不同，不能按证据包顺序猜测原图；本次从MMDU原始图片数组、MMDS原始用户轮次图片顺序取得映射。种子分类及图文语义仍待人工审校。
