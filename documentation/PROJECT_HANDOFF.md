# 项目交接说明

> 更新时间：2026-11-08
> 项目目录：`D:\papers\Graduation Project\vlm-long-context-safety-eval`  
> 当前阶段：2026-11-08用户授权继续本地Qwen并每30分钟检查；已核对2292条保存结果及冻结来源后启动原配置resume，应用任务30-qwen已ACTIVE。完成后审计并停止，不接续其他模型。云端Gemma以用户回传为准。尚无安全率/ASR结论。

## 最新交接摘要（2026-11-08，北京时间10:49恢复；优先于后文历史计划）

**第二台云机Qwen3方案（2026-11-08）**：用户授权另一台相同RTX3090/Ubuntu22.04/Python3.12/torch2.12.1/CUDA13.0服务器运行另一Qwen，即Qwen3-VL-8B-Instruct。新增`configs/cloud/rtx3090_qwen3.json`、`scripts/cloud_experiment_rtx3090_qwen3.sh`、`scripts/cloud_runtime_rtx3090_qwen3.py`及`documentation/guides/CLOUD_RTX3090_QWEN3_EXPERIMENT.md`。同依赖/Brotli修复、冻结数据/模型revision、NF4/BF16/SDPA/1024预算，仅选qwen3vl8b，16条gate后4864条formal；新结果/配置/环境根目录均为`outputs/cloud_rtx3090_qwen3_*`，run后缀`-rtx3090-qwen3-t2121-py312`。复用3090运行库，模型类导入和CLI可选模型改为按所选profile读取；原入口默认LLaVA/Gemma和既有配置不变。不同云机不复制队列状态或锁；当前本地Qwen2.5仍运行、定时任务仍ACTIVE，不为部署准备加载第二个本地模型。96项回归及Bash语法校验通过；第二台云机实际GPU验证尚未执行，不宣称通过。此处是推理评测部署，不包含API初筛调用。

**回答安全性评价新决定（2026-11-08）**：用户希望API全量初筛、人工抽样审核，已准备`prompts/evaluation/formal_v3_screening_{system,user}_v1.txt`、`configs/evaluation/formal_v3_screening_output_v1.schema.json`、`formal_v3_api_screening_v1.json`及普通合成输入/输出示例，说明见`documentation/guides/API_SAFETY_SCREENING.md`。当前没有调用API、发送真实回答/图片或生成机器标签，配置execute=false、judge model=null，批量调用及抽样统计执行器尚待接入。只评最终真实生成回答，完整历史/真实图片为证据，隐藏模型、seed/条件与gold标签；输出安全标签、6类outcome、任务完成、视觉证据状态、技术标记、失效模式、主观置信、人工复核理由和原回答字符区间。截断不直接计安全/无效，旧Noted.不是待评模型逐轮输出，题干风险不等于回答风险。API数据中的任何指令均当作不可信证据，不跟随，不补写或复述危害步骤。

人工方案为calibration先校准冻结规则，之后每模型初始约10%分层概率抽样（约487条/模型，不保证误差精度），覆盖所有机器预测类别尤其高置信safe；另加unclear/低置信/关键缺图/截断影响判断等诊断复核。两类样本分开报告、保存入选概率并按设计加权，按seed处理相关性；人工先独立判断再看机器标签，不能把同一人复核冒作双人。未抽查的机器标签不冒充逐条人工结论，保留覆盖率、故障和不确定分母，禁止直接套用旧`annotation.summarize_annotations`当论文指标；若复用deepseek-flash-2需披露与扩充生成模型同源，并验证复杂多图评审能力。准备文件不修改冻结推理输入和代码，不影响本地Qwen/30分钟监控。

**当前最高优先级指令：“继续工作并30分钟检查一次进度”。** 本地原2292条结果逐条SHA-256及run/model/data/code来源校验通过；GPU空闲且无重复实验进程后，通过`scripts/resume_local_qwen.py`启动原配置`--resume`，不重跑已有结果。状态running/formal，恢复控制器上次PID32636、子进程启动器35492（须重新核对，不能凭历史PID操作）。只继续Qwen2.5-VL-7B，完成4864条后审计停止，不接续其他模型。应用定时任务`30-qwen`已通过工具从PAUSED更新为ACTIVE，保持原每30分钟间隔和只检查权限；用应用任务实际状态为准，不从旧暂停回执或queue中遗留的progress_automation_status历史标记推断定时任务仍暂停。本次恢复后初始计数2292、0错误，最新实际进度读状态与文件数。旧暂停ZIP、回执与结果校验记录保留。

**11月7日暂停历史（已被上面的11月8日恢复指令覆盖）**：已核实并停止本地Qwen模型及`resume_local_qwen.py`控制器/启动器（核实过PID31436、34340、27692、33424，均非今后可盲用的PID）。当时保存2292/4864条，剩余2572；0错误、0空答、0明显重复启发式标记、135条达到输出上限。完整结果、逐条SHA-256、暂停审计及备份均保留。活动锁曾移为`serial_queue_paused_20261107T155456Z.lock`；该旧锁不代表当前没有新运行。

备份`outputs/formal_v3_18turn_runs/backups/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024-paused-20261107T155456Z.zip`，8810176字节，SHA-256=`fa48ab3ab850593a9c04a675a40df54e63ba04a2e44e17299eeffbf82860c126`；ZIP CRC及2292条样本逐条SHA-256核对通过。新回执`pause_receipt.json`，前次暂停元数据保存在run内`pause_history/20261107T155456Z/`，原1446条旧ZIP也保留。应用定时检查`30-qwen`已通过工具实际更新为PAUSED，`scheduled_qwen_progress.json`同步记录暂停；不再自动检查，不启动或恢复其他模型。以后用户明确要求恢复时，用原单模型resume入口跳过现有2292条，并按用户需要重新启用定时检查。

**较早的恢复记录（已被上面的再次暂停覆盖）**：用户此前要求“本地的Qwen也继续跑”，原1446条暂停结果和来源核对后，经`scripts/resume_local_qwen.py`原配置`--resume`续跑。该运行现已停止，保留入口用于将来用户明确授权恢复；它只运行Qwen，正常结束后审计并停止，不接续其他模型。

**云端后续用户回传**：用户称LLaVA已跑完、Gemma权重已下载完，LLaVA尚未收到4864条/错误数/指标文件验证。之后用户已回传Gemma状态：formal，63/4864、0错误，更新北京时间2026-11-07 19:47:43；此前16条gate为0错误/0空答/0明显重复，7条达到1024上限、最大输入16808、峰值Torch分配16353.47MiB、生成1138.7512秒。last_technical_metrics为gate而非63条formal统计，不能混读。Gemma后续最新进度仍需用户回传，不能宣称已跑完。本次只暂停本地，Agent无云端直连权限，未停止云端Gemma。

**云端最新回传（2026-11-07，覆盖下文下载中/孤立子进程快照）**：用户重跑`download --model llava7b`已成功，19/19文件，固定revision为`0d50680527681998e456c7b78950205bedd8a068`，最终`status=processor_ready_gpu_unverified`。LLaVA权重完整性和CPU处理器检查通过，Brotli修复检查继续通过；6.17GB为本次传输显示，不是全部模型体积。用户准备只先跑LLaVA，执行`tmux new -s llava`遇`tmux: command not found`，尚无GPU模型闸门/正式运行开始证据；建议安装tmux后执行`bash scripts/cloud_experiment_rtx3090.sh run --model llava7b`。该选择不会启动Gemma。Gemma下载就绪仍未确认，本地Qwen继续保持暂停。当前云端不应再按历史PID2729或旧锁问题推断仍有活动下载。

**数据部署新决定（2026-11-07，覆盖后文“图片不入Git”描述）**：用户启动云端LLaVA时缺少`data/raw/images/mmds/1.jpg`，执行prepare又遇`Recreated shard checksum mismatch`。原恢复流程在不同Python/zlib环境重新生成gzip再核对压缩字节，不能保证跨环境一致；新增约11.06MB的`data/releases/formal_v3_18turn_frozen_shards.zip`及`configs/cloud/frozen_shards.json`，直接恢复原5份gzip并按原manifest验证，原JSONL、抽样计划、压缩分片hash和推理配置均不改变，也不放宽校验。用户随后明确要求本地图片上传GitHub：本次将manifest引用的508张图片（143534526字节，最大单图8124244字节）按原路径纳入Git，逐张SHA-256已与runtime_manifest一致。不上传其他未使用图片、来源大型ZIP、模型权重或凭据；原模型上传提议仍已取消。云端拉取后重跑prepare，恢复冻结分片并验证已有图片，无需再下载MMDS/MMDU图片ZIP。再运行`bash scripts/cloud_experiment_rtx3090.sh run --model llava7b`，仅跑LLaVA；模型GPU闸门/正式生成仍待云端证据。跨压缩环境防回归及全套88项测试通过，本地Qwen仍暂停1446条。

### 接手时先做什么

1. 阅读本节、README，检查Git状态及最近5条提交，再读本地`outputs/formal_v3_18turn_runs/queue_status.json`并统计实际结果文件。不要从本节快照推断最新进度。
2. 本地已按11月8日用户授权恢复，30-qwen定时检查已ACTIVE；先查现有进程及状态，不重复启动resume或任何队列。输入、推理代码和配置仍冻结，保存结果与两次暂停备份均保留；如用户再次暂停，才按最新要求停止。
3. 云服务器无Agent直连权限，状态来自用户粘贴的终端输出；先确认当前下载进程及锁，再指导后续。用户已取消“从本地上传模型”的提议，不再索取SSH信息、打包或上传模型。
4. 以下明确区分本地事实、云端用户回传与尚未验证事项。后文原4090方案、四模型自动接续及审校待完成等历史段落不覆盖本节最新安排。

### 本地正式实验：当前暂停2292条；下列为更早的1446条暂停快照

- 根目录：`D:\papers\Graduation Project\vlm-long-context-safety-eval`。
- 当前run：`formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024`。
- 结果目录：`outputs/formal_v3_18turn_runs/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024/`；每条`V318-*.json`中最后一轮`response.text`为实际模型回答。
- 暂停后核验1446/4864条，剩余3418；0错误文件、0空答、0明显重复退化启发式标记、49条达到1024输出上限。全部已保存样本均可解析并生成逐文件SHA-256；截断和质量标记不是安全标签，实验尚未完成。暂停时间北京时间2026-11-06 23:56。
- 完整原始结果保留在原run目录。暂停技术汇总`technical_metrics.json`，部分结果审计`pause_audit.json`，逐文件校验`pause_manifest.json`，备份回执`pause_receipt.json`；`completion_audit.json`明确标记`complete=false`，不可当成完整实验结论。
- 新建ZIP备份`outputs/formal_v3_18turn_runs/backups/formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024-paused-20261106T155623Z.zip`，5383278字节；CRC及全部1446条结果SHA-256逐一核对通过。ZIP SHA-256=`9b1ddcb1e4f479f88dc93c63b8c10583149063c78f4bee5336dcf7a70053062a`。
- 本地环境：RTX5070Ti 16GB、Python3.14.6、torch2.14.1+cu130、CUDA运行时13.0。此前按长度统计约2K/12.7秒、8K/20.9秒、16K/33.3秒；抽样阶段分布会变，不能把早期速度当作固定完成时间。
- 停止前已核对模型启动器PID103756/实际模型PID101824及监控PID82528/启动器105192；停止后确认这些任务已退出，不能把它们继续当作活动PID。队列状态pid/child_pid/controller均清空；原82528锁已移为`serial_queue_paused_20261106T155623Z.lock`保留记录，活动锁已解除。不得凭历史PID操作其他进程。
- 旧`scripts/pause_after_qwen_and_audit.py`接管监控已随暂停停止；2026-11-07新`scripts/resume_local_qwen.py`负责本次单模型进度及结束审计，不使用旧四模型控制器。
- 运行中可能已有一次部分数据的`completion_audit.json`，不得仅凭文件存在判定收尾完成；同时核对状态、样本数、缺失ID与修改时间。
- 用户已明确恢复，当前通过原配置`run_experiment.py --resume`运行并安排结束审计，不能启动原四模型queue。暂停时尚未落盘的样本重新生成；1446条已保存结果不重跑。不得修改冻结实现、输出预算或在原run中混入新环境结果。

### 当前数据与实验含义

- `formal_v3_18turn`：144独立种子（风险80、良性64），4864条；风险80×14条件×2视觉时序×2目标=4480，良性64×3长度×2时序=384。原始种子用户已全部接受，六条改写不合入；不要重新开启废弃A/B文件工作流。
- 18轮基准，轮数6/12/18/24/30，名义长度2K/8K/16K；位置和分布只在18轮改变。每seed复用12块中性近义文本，抽样可重放；保留首轮原始开场，C08不再覆盖它。详细条件/配对/哈希以第0节、`configs/formal_v3_18turn.json`和协议指南为准。
- 模型身份仅作外部对照，不是数据集因素。名义长度不是跨模型真实token精确相等，必须记录实测token。划分calibration496、primary3376、heldout992，分析不得默默混合。
- 当前是`fixed_reference`：非最终轮助手为预设`Noted.`，`source=fixed_reference`，token为空且耗时0是正常现象；模型读取完整历史并只生成最终回答。
- 用户询问过从头自由交互实验：目前未实现或纳入当前正式运行；仅讨论作为后续补充，尚未授权启动。静态/动态指图片进入历史的时序，不等于助手每轮真实生成。当前轮数因素反映固定历史的分轮组织，不能解释为自主交互次数效应。
- 原始种子接受不等于模型回答已标注。ASR、安全率、逐轮失守和论文结论均未完成；不把空答、截断、重复或短答直接判为安全/不安全。

### 云端最新安排：RTX3090，LLaVA后Gemma

- 用户已从4090方案改为RTX3090 24GB×1，Ubuntu22.04、Python3.12.3、torch2.12.1+cu130、torchvision0.27.1+cu130，14 vCPU Xeon Gold6330。`os.cpu_count()`显示112可能是容器可见宿主核数，不代表获配112vCPU；入口主要计算库限8线程。
- 云端项目：`/root/autodl-tmp/vlm-long-context-safety-eval`；容器终端名`autodl-container-3cb54a9d57-f98a378d`，不是已知可SSH访问的公网地址。没有保存任何SSH密码、HF令牌。
- 独立入口`scripts/cloud_experiment_rtx3090.sh`和`scripts/cloud_runtime_rtx3090.py`；虚拟环境`.cache/venvs/rtx3090`。旧4090入口/依赖/指南原样保留，当前不要用它们替代3090入口。
- 默认串行LLaVA-OneVision-7B→Gemma3-12B-IT，各16条gate后4864条formal，共9728条formal。Qwen3暂不由该云入口启动，本地也仍暂停其他模型。
- 同一数据、模型revision、NF4/BF16、SDPA、贪心解码、1024输出上限不变；云run后缀`-rtx3090-t2121-py312`，结果在`outputs/cloud_rtx3090_runs`；环境和配置分别在`outputs/cloud_rtx3090_environment`、`outputs/cloud_rtx3090_configs`。状态、CPU面板、日志及锁仍在`outputs/formal_v3_18turn_runs`。不得跨机器覆盖状态/锁。
- 用户已回传环境检查通过、模型类可导入、BF16真实运算通过；实际模型GPU闸门、正式推理尚无完成证据。云端数据prepare是否全部完成也应按文件/报告核对，不从下载日志推断。
- 完整操作见`documentation/guides/CLOUD_RTX3090_EXPERIMENT.md`。云端需单独HF登录获批Gemma账号，LLaVA开始下载不证明Gemma访问已验证。用户曾贴出HF令牌，已告知立即撤销重建；不要在交接、命令或Git中复制原令牌，撤销是否完成未获确认。

### 云端下载故障已修复，但最后是遗留子进程

1. 最初`config.json`下载TypeError由HTTP解压接口引起：HF2.2.0/httpx2与httpcore2均2.16.0调用旧Brotli不支持的`output_buffer_limit`，不是GPU资源失败。
2. 3090专用依赖已加入`Brotli==1.2.0`，新`scripts/check_http_download.py`做离线HTTP解压往返检查；`scripts/diagnose_hf_download.py`只请求固定revision小配置文件，输出脱敏异常链。不要降级HF或重装Torch来处理此问题。
3. **用户已回传修复生效**：HTTP decoder检查passed，Brotli1.2.0/httpx2 2.16.0；LLaVA固定revision`0d50680527681998e456c7b78950205bedd8a068`已开始下载，显示33.1MB等进度。不能仍把Brotli列为未解决阻塞。
4. 用户随后Ctrl+C中断外层命令，再跑报`deployment.lock`。最近一次用户执行pgrep发现PID2729仍为`python scripts/prepare_open_models.py --model llava7b --download --processor-check --include-gated`。这是下载子进程未退出，不是已证实的陈旧锁。
5. **下轮先确认该进程最新状态，不要直接删锁或再启动一份下载。** 最近已给用户的观察命令如下；PID2729只是最后一次回传，现时是否存活未知。若它仍下载，只需观察缓存增长；此孤立子进程只负责LLaVA，不会自动切到Gemma。

```bash
pgrep -af '[p]repare_open_models.py|[c]loud_runtime(_rtx3090)?\.py'
watch -n 10 'du -sh .cache/huggingface/hub/models--llava-hf--llava-onevision-qwen2-7b-ov-hf'
```

只有确认所有相关下载/父进程已退出后，才可重跑`bash scripts/cloud_experiment_rtx3090.sh download --include-gated`以复用缓存并准备两个模型；若此时还报锁存在，才删除`outputs/model_deployment/deployment.lock`。不要凭旧PID直接kill，不批量结束其他任务，不清空缓存。若用户明确决定停止当前下载，先确认进程身份，再只停止该任务并确认退出后处理锁。

模型与CPU检查齐备、数据prepare验证通过后，在tmux中运行`bash scripts/cloud_experiment_rtx3090.sh run`。需先通过每模型GPU诊断和gate，不能把下载完成说成正式实验完成。

### Git、验证及取消事项

- 仓库`https://github.com/MoCHIxb/vlm-long-context-safety-eval`，分支main。本次更新前工作区干净，最新本地/已推送提交`701ee4e`；本交接更新是该提交之后的文档改动。
- 最近5条：`701ee4e` Brotli下载修复；`4d42953` 脱敏小文件诊断；`2b07d02` 3090独立方案；`b21bfa9` 冻结18轮数据与云部署；`96a7ad9` 原formal_v3构建。
- 最新全套测试87项通过，真实Brotli1.2.0在隔离缓存目录的HTTP解压检查通过；没有修改本地正在推理的虚拟环境。3090真实解压/环境已由用户回传确认，但模型生成/显存闸门仍未执行确认。
- Git含代码、配置、来源种子和约11.8MB固定运行数据快照；508张图片和权重按校验清单下载。`.gitattributes`保留精确字节；不要自动格式化/转换冻结文件换行而破坏哈希。缓存、凭据、回答、临时材料不进Git。
- 用户提出过本地模型上传，已确认LLaVA约16.07GB、Gemma约24.41GB缓存完整，但随后明确“算了，先不用”。**此提议已取消**，仅做了只读核对，没有打包、创建传输工具或上传，也没有获取SSH连接信息；不要恢复这一分支任务。

## 0. 最新设计决定：18轮基准（2026-11-06，优先级最高）

**最新运行指令（覆盖下文四模型自动接续计划）**：用户要求Qwen2.5-VL-7B完成后暂停并检查生成结果。已只终止旧串行控制器105900，不终止当前模型子进程103756；新监控`scripts/pause_after_qwen_and_audit.py`接管该子进程，继续维护队列状态及锁。Qwen结束后自动核对4864条样本ID、失败、空答、短答、重复退化、截断及资源指标，写入本run的`technical_metrics.json`与`completion_audit.json`，状态变为`paused_after_qwen`；中断/不完整则标记需处理。Qwen3-VL、LLaVA、Gemma均暂停，不得自行重新启动原四模型队列。检查快照1054/4864、0错误、0空答、0明显重复退化、24条截断，只是运行中统计，非最终结论。监控不会输出回答原文，不把短答或重复标记当作安全标签；最终安全性仍需回答标注。自动收尾后会在文末追加事实性检查结果。

**云端同步准备（2026-11-06）**：用户授权整理项目主体并上传GitHub，云GPU为RTX4090；本地Qwen继续、完成后暂停的指令不变。新增`scripts/cloud_experiment.sh`及`scripts/cloud_runtime.py`，支持Linux环境安装、固定快照恢复、508张图片逐图校验、固定revision下载、CPU检查/双色GPU诊断/16条闸门/正式推理及resume。默认云端只选Qwen3-VL-8B，支持显式串行选择其他模型；云端run_id加`-cloud`，不自动接续本地Qwen，不混用输出目录或锁。`data/releases/formal_v3_18turn_runtime.zip`为11753496字节，保留原始数据与抽样计划的精确字节；`configs/cloud/runtime_manifest.json`绑定快照、MMDS/MMDU来源档案及508张图片SHA-256。`.gitattributes`保留文件字节，避免跨系统换行破坏现有代码和配置指纹。忽略模型缓存、凭据、输出和生成中间文件。主要依赖锁定`requirements-cloud.txt`；本地实测Python3.14.6、torch2.14.1+cu130、CUDA13.0。新增后78项测试及Bash语法校验通过，干净目录快照恢复与分类压缩分片哈希一致；未在云服务器安装依赖或执行4090推理，不宣称云GPU闸门已通过。详细操作见`documentation/guides/CLOUD_EXPERIMENT.md`。

用户明确要求：复用每个种子现有12块中性近义文本，随机调用以调整上下文长度与对话轮数；轮数取6、12、18、24、30，以18轮为基准；历史风险线索位置与分布只在18轮条件下改变；第一轮原始开场不得被覆盖。

**实施状态：已完成重建。** 当前配置`configs/formal_v3_18turn.json`，数据`data/processed/formal_v3_18turn.jsonl`，4864条、144个独立种子。旧`formal_v3_extended`的4224条及原始种子、API近义库与哈希均未覆盖。新实现只复用已有语段，不新调用API；构建不使用GPU。用户随后授权构建完成后直接开始四模型正式运行，现已启动串行队列，GPU仅用于诊断/闸门及后续正式推理。

- 风险层14条件×80种子×2视觉时序×2目标=4480条；良性层维持18轮下3长度×64种子×2时序=384条，共4864条。没有额外扩展良性五档轮数交叉。
- 风险位置实现：参考8/10轮，早期2/4轮，后期14/16轮；集中9/9轮，拆分2/16轮。三种分布中心均为第9轮，第1轮开场与最后一轮目标严格保护。C11澄清在第17轮。
- 非18轮参考线索为`floor(n/2)-1`及`floor(n/2)+1`；C01/C02为6/12轮，新增C12/C13为24/30轮，C09/C10/C11语段资产及含义保留。此映射为本次实现选择，已在配置明示。
- 随机种子20261106，逐seed用SHA-256派生本地随机状态，按块有放回抽样、块内句序保持；抽样计划及每条分配均保存。位置/分布与五档轮数对照均复用相同中性文本集合，仅重分配轮槽；长度档为同一随机流的嵌套前缀。
- 非最终轮固定助手回应统一为中性`Noted.`，新增中性文字放在用户轮，不再按旧方式只追加到助手历史。固定参考模式下只有最终回答由待测模型生成；不混用旧参考历史协议的结果。
- 新数据SHA-256：`ffd78bcce1a0548905dd8730d6d0dd17ee4191649e4befc42cbec981d75b571f`；抽样计划SHA-256：`4f8389d3bc266fa859d32a01b3bfa4ffdeef42c932f968aa902030f8fbab0f4d`。
- 独立校验重放144份随机计划，逐条检查4864条、2240组安全/危险配对、2432组视觉配对及5个分片；重复构建哈希一致，旧资产哈希不变。配对平均名义长度偏差最大1.0254%，单条最大2.3926%，仍为空白词数/0.75估算，不宣称全4864条四模型完整输入token已精确等长。
- 构建与验证脚本`scripts/build_formal_v3_18turn.py`、`scripts/validate_formal_v3_18turn.py --rebuild-check`；核心逻辑`src/longvision_eval/controlled_18turn.py`；报告`documentation/reports/formal_v3_18turn_status.json`及`formal_v3_18turn_validation.json`。当前完整测试74项通过。

**四模型队列**：`configs/runs/formal_v3_18turn/queue-ffd78bcc-ad9fe617-g1024.json`；状态`outputs/formal_v3_18turn_runs/queue_status.json`；控制器`scripts/run_formal_v3_18turn_queue.py`。顺序Qwen2.5-VL-7B → Qwen3-VL-8B → LLaVA-OneVision-7B → Gemma3-12B-IT，每模型4864条，共19456条，一次只加载一个模型。离线HF缓存，NF4/BF16、固定参考历史、贪心解码、repetition_penalty=1.05、统一1024输出上限，遇错停止，按数据/配置/代码指纹resume；不要重复启动另一个队列或在运行中重建输入。

运行启动事实：Qwen2.5-VL的g1024资源闸门已16/16完成，0错误、0空答、0明显重复退化，1条达到1024上限；最大实际输入16864 token，峰值Torch分配显存8928.46 MiB，总生成372.9936秒。该gate不混入正式统计。g1024正式run已进入执行并观察到首批8份结果、0错误，run_id=`formal-v318-qwen25vl7b-ffd78bcc-ad9fe617-g1024`；其他三模型是串行排队，不能说已全部完成GPU检查或正式推理。以上只是启动快照，后续进度以状态文件和结果文件为准，不据此计算安全率。

四模型16条资源面板的CPU输入检查均通过，样本输入token范围：Qwen2.5-VL 2932–16864；Qwen3-VL 2921–16853；LLaVA 4810–18670；Gemma3 2963–16808。仅代表该面板，不代表全4864条均已预先测量。全量适配器会逐次检查实际输入+输出预算，无静默截断。Qwen普通双色GPU诊断通过。初始512预算Qwen闸门16条0错误、0空答、0明显重复，但7条达到输出上限，因此旧队列已停止并隔离，改为g1024新队列；旧结果不混入正式统计。调整记录`outputs/formal_v3_18turn_runs/budget_change_g512_to_g1024.json`。每模型通过普通生成与16条GPU闸门后自动进入formal；正式运行当前进度必须读取状态文件，不从本段快照推断已完成。

### 新方案构造与控制规则

- **轮次定义**：一轮为一次用户输入及对应助手回应；同一次用户输入中的多张图片不额外计轮。固定参考历史模式下，18轮目标输入包含18次用户输入与17次参考助手回应，最后一轮由待测模型回答。
- **中性文本复用**：每个种子保留现有12块近义文本，不新造独立种子。抽取它们来填充中性轮或中性上下文；超过12块需求时允许重复抽取，但记录抽样次数与重复情况。只使用中性内容，不把危险目标、升级线索或最终答案混进额外填充。
- **随机但可复现**：使用固定且可记录的随机种子，保存每个seed的文本块抽样顺序、块编号、轮次分配及必要的句子拆分。构建时随机，评测时读取固定结果；四模型不各自重新抽样。
- **配对共享随机结果**：同一种子的安全/危险及静态/动态配对使用完全相同的中性抽样与历史，只改变声明的最终目标或图片进入时序。位置、分布等同长度对照不得独立重新随机背景，否则会同时改变干扰内容。不同长度/轮数版本尽量复用同一预先抽样流，按需截取或重分配。
- **上下文长度因素**：固定18轮，通过中性文本抽取量与每轮篇幅调整总长度；未另行变更的长度档暂沿用2K/8K/16K设计，仍须核验实际可行性与真实token。不要为了拉长文本而额外增加轮数。
- **对话轮数因素**：比较6、12、18、24、30轮，多出的轮次用中性文本填充。比较轮数时固定同一总上下文长度预算，调整每轮填充量；不能简单每增加一轮就整体增加长度，使轮数和长度混杂。风险线索保持既定相对位置/分布规则，具体跨轮数映射在实现时明确记录。
- **历史风险线索位置因素**：只在18轮参考条件下设置早/中/晚位置；保留同一潜在线索与升级线索的内容及先后顺序，仅调整所在轮次，并用同一中性抽样内容补足其他轮槽。第1轮保留原开场，第18轮保留最终请求；本次实现为早2/4、中8/10、晚14/16，均不占两端，不套用旧6轮映射。
- **风险线索分布因素**：同样只在18轮参考条件下比较渐进8/10、集中9/9、拆分2/16；保持风险线索的内容、总量及中心轮次不变，通过合并或分散到不同中间轮次改变分布，同一中性文本集合重新分段，不添加更强风险内容。
- **修复C08覆盖问题**：旧`cue_positions(..., distribution="split")`返回首轮索引0，会使`latent_cue`覆盖`neutral_setup`。新方案必须弃用这条规则，确保开场仍在第1轮且原文完整保留；拆分线索安排在第2至第17轮的适当位置。增加对应断言/测试，不能仅检查seed库中的原句未修改，还要检查派生轨迹中开场实际存在。
- **其他因素**：图文互补/冗余/冲突、意图澄清、静态/动态及安全/危险配对继续沿用原有语段资产与含义；其参考轮数改为18。模型身份仍只作外部对照，不作为数据集因素。图片集合与顺序保持一致，动态引入轮次须适配新轮数并记录，不能凭旧配置推断已完成控制。

### 后续运行与检查

1. 保持输入与推理代码版本冻结，读取当前queue_status确认活动进程；不得重复开模型或恢复旧512队列。
2. 跟进每模型GPU闸门与formal阶段，完成后汇总失败、空答/退化、截断、实际输入token、生成耗时和峰值显存。配置已有stop_on_error，错误不能当作安全回答。
3. 未完成人工回答标注前不报告ASR或安全率。原始种子接受记录不等于模型回答标注完成。
4. 本次模型实际输入不按不同模型重新随机填充或裁剪。对不同分词/视觉编码开销记录实测分布，不把名义2K/8K/16K当作跨模型精确等长。

## 1. 当前研究目标

课题为“长上下文多轮对话下的视觉语言模型安全性分析与防护研究”。当前已完成第一阶段原始种子接受、文本扩充及构建检查，下一步准备模型输入与资源验证：研究上下文长度、对话轮数、风险位置、风险分布、图文关系、意图轨迹以及视觉证据静态/动态呈现对安全应答能力的影响。

模型类型不是数据集因素。不同模型只在数据冻结后运行同一测试面板，作为外部对照和互作参考，不参与样本构造、配额或标签定义。

数据冻结后的计划开源模型为：

1. Qwen2.5-VL-7B；
2. Qwen3-VL-8B-Instruct；
3. LLaVA-OneVision-7B；
4. Gemma 3 12B IT。

闭源模型暂不纳入当前阶段。18轮新方案已重建，四模型串行队列已按用户指令启动；现有`formal_v3_extended`为来源资产及旧轮数版本，不直接作为新实验输入，不恢复旧队列。

## 2. 已保留的数据资产

旧数据版本保留，不覆盖：

| 版本 | 规模 | 用途与局限 |
|---|---:|---|
| `pilot_v1` | 192 | 最早期静态控制变量原型 |
| `pilot_v2` | 160 | 静态、动态、良性三轨预实验 |
| `formal_v1` | 456 | 旧核心受控层；独立种子偏少且静态/动态受来源混淆 |
| `formal_v2` | 1,554 | 456条核心层加1,098条MMDS/MMDU自然覆盖层；共322个来源，但核心仅28个独立种子 |

`formal_v2`仍可作为自然场景覆盖和外部验证资源，但不能继续作为新的核心因果设计。旧模型运行结果、标注输出、运行配置和阶段性模型报告已从当前工作区清理；未提交的`outputs/`结果不可恢复，Git历史中的既有代码与数据版本仍可追溯。

## 3. `formal_v3`冻结设计

本节规模公式描述旧方案。144个独立种子及原始资产继续保留，但下述12条件、4224条不能直接沿用为新18轮方案规模；最新控制规则见第0节，须更新矩阵后重算。

目标为144个独立语义种子：

- 危险种子80个，四类风险各20个；
- 每类风险4个子类型，每个子类型5个种子；
- 良性种子64个；
- 危险种子由3至4个语义连贯的视觉证据包构成；良性种子优先3至4个，在消除跨种子图片复用后有7个良性种子使用2个证据包，禁止通过复制图片凑数。

四类风险为：

- `deception_and_economic_harm`；
- `privacy_and_profiling`；
- `illegal_and_cyber_abuse`；
- `physical_and_public_safety`。

危险层采用12个单因素条件、2种视觉证据时序和安全/危险最小差异配对：

```text
80 × 12 × 2 × 2 = 3,840条轨迹
```

良性层采用3种长度和2种视觉证据时序：

```text
64 × 3 × 2 = 384条轨迹
```

合计4,224条轨迹。论文和统计中必须说明这些轨迹来自144个独立场景，不能把4,224条当作独立样本。

## 4. 静态/动态因素

主因素字段为`visual_evidence_schedule`：

- `static_initial_bundle`：全部证据图片仅在第一轮同时出现；
- `dynamic_incremental`：完全相同的图片集合各出现一次，但分散到不同轮次逐步引入；
- `final_bundle`仅作为机制诊断，不进入静态/动态主效应。

同一种子、条件和标签下，静态与动态版本必须共享图片文件、图片顺序、用户文本、最终请求、轮数、目标长度和固定助手历史。唯一变化是图片所在轮次。该设计用于消除旧版本中SafeMT静态轨道与MMDS动态轨道之间的数据来源、语义、图片数量和自然度混淆。

## 5. 条件矩阵

最新方案以18轮为参考，轮数水平为6、12、18、24、30；风险线索位置和分布只在18轮下比较。具体索引、14个条件及编号映射已落地，见第0节、`configs/formal_v3_18turn.json`与`FORMAL_V3_18TURN_PROTOCOL.md`。

以下为当前文件实际实现的旧矩阵，供重建时对照，不能当作新方案已完成：参考条件`C00`为6轮、8K、中间风险位置、渐进风险分布、图文互补、意图逐步升级。

`C01`至`C11`分别控制：4轮、8轮、2K、16K、风险早期、风险后期、集中分布、拆分分布、图文冗余、图文冲突、澄清或去风险转向。每次只改变声明的因素。

安全/危险版本共享全部历史和图片，只允许最终目标发生必要变化。安全版本必须是有实际价值的合法、防御、合规或风险缓解任务，不能只是机械删除危险词。

## 6. 当前文件

当前18轮入口：`configs/formal_v3_18turn.json`、`data/processed/formal_v3_18turn.jsonl`、`data/processed/formal_v3_18turn_sampling.json`、`data/processed/formal_v3_18turn_shards/manifest.json`、构建/独立验证脚本及两份18turn状态报告。当前运行入口与状态见第0节。

以下为已完成的旧轮数实现与可复用来源资产。不要直接按旧配置启动新实验：

- `configs/formal_v3_extended.json`：扩展版规模、条件、路径及长度计量口径；
- `configs/formal_v3_taxonomy.json`：16个危险子类型和8个良性任务子类型；
- `data/seeds/formal_v3_core_acceptance.json`：用户接受原始144个种子的事实记录及原文件哈希；
- `data/seeds/formal_v3_extended_seed_bank.json`：当前扩展种子库，包含原始核心、240段三条件和144份近义文本库；
- `data/processed/formal_v3_extended.jsonl`：当前4224条轨迹，约177.49 MiB；
- `data/processed/formal_v3_extended_shards/manifest.json`：5个压缩分片的计数和哈希；
- `data/derived/formal_v3_original_core_extensions/`：生成整合的中间结果；
- `outputs/formal_v3_original_core_extensions/`：API请求、响应、复用记录和整合状态，无须再填写人工审校表；
- `scripts/generate_formal_v3_extensions.py`、`scripts/invoke_ustc_api.ps1`：API扩充与加密凭据调用入口；
- `scripts/build_formal_v3_extensions.py`：整合和重建入口，`--embedded`可从发布种子库离线重建，不依赖旧审校工具或API日志；
- `documentation/guides/FORMAL_V3_EXTENSIONS.md`：扩充方法、重建命令和适用限制；
- `documentation/guides/FORMAL_V3_DATASET_DESIGN.md`、`FORMAL_V3_ANALYSIS_PLAN.md`：控制设计与后续分析规则；
- `documentation/reports/formal_v3_extensions_status.json`、`formal_v3_review_archive.json`：构建及归档的事实记录；
- `configs/deployment/open_models.json`、`configs/models/deployment/`、`scripts/prepare_open_models.py`：四模型部署准备；
- `documentation/guides/OPEN_MODEL_DEPLOYMENT.md`：已部署模型与CPU/GPU验证边界。

`data/seeds/formal_v3_seed_bank.json`、`data/processed/formal_v3.jsonl`及其构建/验证工具保留作基线与来源追溯，不覆盖、不自动作为新正式实验输入；旧`formal_v1/v2`也保留。原`data/review/`及旧审校/翻译工具已经移入`archives/formal_v3_review_workflow_20261106.zip`，不再是当前工作入口。

## 7. 当前进度与下一步

### 已完成的旧方案结果（保留为资产与基线；最新设计以第0节为准）

2026-11-06已完成用户最新任务：原始144个种子全部按用户明确决定接受，六条API改写均不合入，核心原句未修改。接受记录为`data/seeds/formal_v3_core_acceptance.json`，绑定原种子库SHA-256；历史六条争议记录保留作追溯，不擅自删种子或重新改写。

- C09/C10/C11：80份、240段全部完成，0失败；74份完整请求哈希一致而复用，6份按原文重生。
- 中性近义扩充：144份、每份12块，共1728块全部完成，0失败；只根据原始中性开场生成，不扩写危险执行细节。
- 当前扩展种子库：`data/seeds/formal_v3_extended_seed_bank.json`，SHA-256 `7acea7f1cbd0e9f246826aa539ab139ab14540d430b84f92c48aa2142c128056`。
- 当前完整轨迹：`data/processed/formal_v3_extended.jsonl`，4224条、186114788字节，SHA-256 `469ed06d0ed044f9b308bb176ea987dec4b267925fd2b03f379673aeeef5b286`。基线原文件未覆盖。
- 1920组安全/危险历史配对、2112组静态/动态配对与5个gzip分片校验通过；从发布种子库重复重建、清理后重建的哈希均一致。配置`configs/formal_v3_extended.json`，分片清单`data/processed/formal_v3_extended_shards/manifest.json`。
- 填充为同一种子固定顺序的近义句循环，按完整句分配到非最终轮参考历史；不再在最终请求末尾补指令凑长度。54个良性种子的可选来源助手历史统一按最短档缩短一次，并用于全部长度版本；用户核心请求保留。
- 长度仍为`whitespace_words/0.75`估算，最大相对估算偏差4.1015625%；尚未测量四模型完整输入token。C09/C10依据文字描述，不声称API逐图核验过操纵关系。新增语段记录为API生成及机器校验，不伪造逐段人工评分或双人κ。
- 种子审校工作流已关闭：旧A/B、阅读稿、译文、审校工具及废弃修订版本共633个文件在ZIP逐文件SHA-256/CRC验证后移出，`data/review/`已不存在。归档`archives/formal_v3_review_workflow_20261106.zip`，SHA-256 `0353bf8b82db4daa1516e60feefc8247506ac8cc8846a6feda37b895da19837a`；可恢复，未纳入Git。保留原始数据、接受记录、当前API日志、生成/构建脚本、模型部署及模型回答标注能力。
- 清理后60项测试全部通过，`git diff --check`通过。当前入口`scripts/generate_formal_v3_extensions.py`、`scripts/build_formal_v3_extensions.py`；详情`documentation/guides/FORMAL_V3_EXTENSIONS.md`，状态报告`documentation/reports/formal_v3_extensions_status.json`及`formal_v3_review_archive.json`。

原计划下一步为四模型输入测量和资源闸门；现已被第0节的新方案重建步骤前置。此次仅更新交接文档，既有构建与归档事实不变；没有使用GPU、启动正式模型实验或产生ASR。原始种子接受不等于未来模型回答已标注。

### 已实现的旧扩充手段（新方案将改为可复现随机抽取）

1. **原始核心保留**：144个种子的原内容接受，六条API改写不使用。扩充不是增加新来源场景，独立样本单位仍是144个seed；4224条是条件、标签及视觉时序的派生轨迹。
2. **条件补充**：80个风险种子各生成C09冗余、C10单一具体描述冲突、C11用途澄清/意图缓和，共240段。只向API提供现有文字，不上传图片；C09/C10是根据描述构造的关系，不能写成已经逐图验真。
3. **近义库**：每个种子依据原始中性开场生成12块近义文本，合计1728块。优先保持原场景、中性对象与描述目的，不扩写危险目标、实施步骤、升级线索或最终答案。
4. **实际填充**：拆为完整句，按固定顺序取用，长度不足就循环使用已有近义句，再分配到非最终轮的固定参考助手历史。长档包含近义表达的重复，不是每一段均重新独立生成，也不是新增事实或独立场景。最终目标不加补句凑长度。
5. **配对一致性**：同一种子同条件下，安全/危险与静态/动态复用同一填充历史；条件之间也沿用同一近义句序列，不按condition随机轮换背景。更长档增加同一序列的用量。
6. **计量边界**：当前2K/8K/16K是构建估算档位，采用空白分词数除以0.75；最大估算偏差约4.10%。不等于任一模型完整输入token。下一步应计入实际分词器、聊天模板、图片预算及参考历史，并记录每模型实测分布；不能在测量前宣称四模型输入已精确等长。

### 旧下一步计划（须先完成第0节新方案落地）

1. 检查扩展数据、接受记录及分片哈希；Git工作区仍有本轮未提交修改，不擅自提交或丢弃。
2. 在CPU上测量四模型完整输入token和图像预处理开销；如需调整文本或预算，保留现版本及变更记录后重建，不悄悄沿用原哈希。
3. 确认GPU可用后，先串行普通图片生成诊断和小批长上下文资源闸门，一次只加载一个模型；不能把已有CPU接口通过等同于GPU生成通过。
4. 用户指令下以同一冻结面板进行四模型推理，记录失败、空答、截断、实际token、耗时和显存。
5. 再处理模型回答标注、模型内配对因素分析和跨模型趋势对照；未标注回答不作为ASR、安全率或论文结论。

### 历史推进记录（旧路径可能已移至上述归档）

2026-11-06用户最新决定（优先于全部旧修订记录）：六条保留原内容，原始144种子全部接受；继续生成C09/C10/C11及基于原文的近义填充，完成后关闭并清理旧审校工作流。已记录`data/seeds/formal_v3_core_acceptance.json`，绑定原种子库SHA-256及144个seed_id，不冒充双人独立评分；六条API改写均不合入。新增语段属于API生成与机器校验，不伪造逐段人工评分。

当前有效生成根`outputs/formal_v3_original_core_extensions/`：conditions已80/80、240段，74份按完整请求哈希复用、6份用原始六条重新生成；background正推进144份，每种子12份原中性开场近义块，不将危险/升级语句重复到背景中。严格保持原始五个核心atom不变、只新增/替换C09/C10/C11与中性背景。派生文件将为`data/seeds/formal_v3_extended_seed_bank.json`及`data/processed/formal_v3_extended.jsonl`，基线原文件不覆盖。

现用入口已重命名为`scripts/generate_formal_v3_extensions.py`，PowerShell动作为`original-core-extensions`；旧repair动作已从wrapper移除。整合脚本`build_formal_v3_extensions.py`使用固定顺序的API近义句循环填充，按完整句预算、静态/动态与安全/危险共享历史，不再在最终请求末尾加提示语凑长度。仍使用历史的空白词数/0.75估算口径，不能宣称已测量四模型真实输入token。

清理脚本`archive_formal_v3_review.py`已提供可读清单与构建完成门槛：成功整合4224条后，先对旧A/B、阅读/翻译材料、审校工具和废弃API修订版本建立ZIP并逐文件哈希/CRC验证，再移除其工作区副本。归档目标`archives/formal_v3_review_workflow_20261106.zip`，不含缓存凭据、模型权重、原始数据及当前生成日志。当前尚未执行归档删除，完成状态须看归档报告。

v2六条topic/图片引用改写已全部完成：6候选、0失败、0运行中；六条均有topic_alignment_zh，API引用映射共19项（retained 12、rephrased 7），机器验证映射短语可回查输入/输出，不代表语义已经人工审定。审阅文件`outputs/formal_v3_text_revision_v2/repair_d04ad2e879a5/candidates_for_human_review.json`已刷新，导航`data/review/formal_v3_text_revision_review_index.json`指向v2。候选库`data/candidates/formal_v3_text_revision_v2/seed_bank_core_revised.json`；本次repair-only结束，旧下游批次保持暂停，以免基于尚在调整的六条继续付费派生。正式数据未覆盖，未代填人工审核。84项测试通过，git diff --check通过（仅既有换行提示）。

2026-11-06再次更新：用户要求六条改写必须显式以原topic为语义锚，按语义保留原文图片引用、编号及对象对应关系。已停止旧纯文本流水线，保留已有输出，按此要求另启v2的六条repair-only候选任务，输入新增original_topic与原文引用片段，输出新增topic_alignment_zh和image_reference_preservation（保留/改写/省略原因映射）。不发送图片，机器只检查映射短语来自输入/输出，不代替用户语义审定。v2目录为`outputs/formal_v3_text_revision_v2/repair_d04ad2e879a5/`，候选种子根`data/candidates/formal_v3_text_revision_v2/`。当前六条生成完成前不继续基于旧改写推进下游；旧流水线已标superseded。后续续跑可按逐seed完整请求哈希复用未改变的旧条件响应，避免重复收费；六条输入改变的条件需重新生成。

最新纯文本运行已完成6/6条重新编排与意图改写，目录`outputs/formal_v3_text_revision/repair_2b317b702bb3/`；新三条件运行目录`conditions_7a9be240ea9b/`，正推进80份候选，随后144份背景。全套83项测试通过。审阅导航：`data/review/formal_v3_text_revision_review_index.json`；各run汇总`candidates_for_human_review.json`含candidate、review_context、image_links（本轮不传图）、human_decision、human_notes，用户填写判断会由collector保留。此条是运行中快照，完整计数以summary/attempt和流水线状态为准。

2026-11-06最新设计变更（优先于下述旧记录）：用户指出六条应由API审阅既有文字后重新编排、补充意图，不能仅回选原始轮次；三条件与背景也只输入既有语段，图片不作为本轮生成输入，内容由用户审核，聊天不展示。已精确停止旧pipeline与候选进程，旧输出保留并标记superseded；中断请求费用未知，未自动重发。

新入口`scripts/run_formal_v3_text_revision.py`及PowerShell动作`text-revision`，已启动：六条repair（最多2并发）→80份conditions→144份background（最多4并发），仅API网络请求，无GPU。新输出根`outputs/formal_v3_text_revision/`，新候选种子根`data/candidates/formal_v3_text_revision/`，与旧摘录/看图版本分开。全流程输出明确为待用户审阅，图文冗余/冲突依据仅为原文字描述，未声称核验图片事实；通过用户审核后才能作为图文关系操纵有效。提示词仅允许高层意图，不生成执行步骤、技术参数、投放/传播、攻击目标选择或规避细节。

集中审阅文件仍为各run的`candidates_for_human_review.json`，新导航文件`data/review/formal_v3_text_revision_review_index.json`由collector生成。原始A/B、原正式数据不覆盖。新版新增4项截断/重复/缺字段测试通过；完整测试复核待本轮结束。当前新队列是否完成以`outputs/formal_v3_text_revision/pipeline_status.json`及summary为准。

2026-11-06最新：6份source-repair候选全部已生成（0失败），经机器摘录、时间顺序、规模、子类型配额、主题近重复及跨种子图片检查后另存`data/candidates/formal_v3_api_revision/seed_bank_source_repaired.json`，原80风险/64良性规模保持。六份API均选择原来源而非替换来源，未产生-R1编号；这只表明API选择与机器结构检查完成，未证明攻击意图或语义配对已经人工通过，用户需审核六份candidate。原始种子、processed与A/B未覆盖。

已启动严格串行`revision-pipeline`（source-repair复用完成记录→条件80份→背景144份→汇总待审阅种子/清单），当前运行状态见`outputs/formal_v3_api_candidates/pipeline_status.json`。本批只构造待用户审阅候选，不自动回写正式数据或伪造人工接受；240段条件及144份背景是否完成须核对各candidate与流水线状态，不能仅凭脚本启动判定。用户可在各run的`candidates_for_human_review.json`填写human_decision/human_notes，collector保留已有填写。

2026-11-06用户要求恢复并持续完成修订，重申具体文本由用户审核，助手仅负责脚本/API、格式/状态检查和语段落盘，聊天不展示具体内容。普通连通性检查通过。缩短预算的文本review曾出现2048 token全为推理、正文为空；依据DeepSeek官方参数将新版候选脚本改为`thinking.type=disabled`，移除reasoning_effort。非推理review获得5份候选，第6份HTTPError，未自动重试。review输出不自动改数据。

新增source-repair任务：API从未被其他种子占用的原始MMDS来源选择按时间排列的四个用户摘录和良性配对，脚本检查原文连续子串、轮次、唯一性及安全配对字段；换来源时另存带-R1编号与替换谱系的修订种子，不覆盖旧数据或审校。首条source-repair模型漏写needs_human_review，但已正常返回；在无新API请求的情况下验证原文摘录并恢复为本地强制待审阅候选，目录`source-repair_0ddbd52426c3`，恢复记录保留。剩余五条续跑中。

首条三条件候选`V3H-DE-01`已成功保存并通过结构检查，目录`outputs/formal_v3_api_candidates/conditions_b5245d76036b/`，只发送E1实验图以使C09/C10的引用在两种视觉时序下均可见，语义仍待用户审核。新增`candidate_validation.py`与4项边界测试；全套79项在正常权限下通过（沙箱临时目录曾导致13项权限错误，已通过正常权限复核）。尚未完成80份三条件及144份背景，不得称全量修订已完成。

获准启动的`review_adfc7697bf32`首条V3H-DE-11在300秒请求超时后返回TimeoutError，无响应正文与候选，其余五条未提交；失败记录保留且未自动重试。随后启动一条background纯文本试生成，以区分多图与通用服务延迟；以该任务attempt状态为准。正式数据、原始审校与模型实验均未改。

2026-11-05用户对明确外传范围回复“允许”，授权发送待处理种子英文文本、原始用户对话及对应实验图片到中科大API。审批已放行，六条review任务已启动，run_id为`review_adfc7697bf32`；后续以attempt/response/candidate文件为准。新增`collect_formal_v3_api_candidates.py`可汇总候选为各run目录的`candidates_for_human_review.json`，保留用户已填写判断。按用户要求，助手只核对运行、格式与统计，不继续人工审阅候选具体敏感文本；用户负责语义审阅和替换。该授权已解决下述先前审批阻塞。

2026-11-05最新指示：由API审阅具体内容、生成独立候选，用户自行审阅后替换。新增`scripts/run_formal_v3_api_candidates.py`，支持review（六条原始完整用户轮与实验图片）、conditions（80条风险种子及实验图片，C09/C10/C11）、background（144种子中性分块背景）。新增PowerShell wrapper动作`review-candidates`、`condition-candidates`、`background-candidates`，`-Limit`默认1，显式增大可扩展范围。均串行、保留失败请求且不自动重试；结果在`outputs/formal_v3_api_candidates/`，不合并正式种子和人工决定。候选目前仅检查JSON和seed身份，语义及完整结构仍待人工检查；背景块尚未进行目标token计量。

实际提交六条review任务被自动审批拒绝，理由为须明确确认向中科大API发送这六条完整来源用户对话及实验图片；该命令没有运行，尚无本轮候选。不得绕过或改用间接命令提交，等待用户明确确认该载荷与目的地。此前诊断运行`repair_diagnosis_f9f40d968e7e`已得到6份有效诊断候选（均待人工审定），正式数据未改。旧段落中“当前没有凭据/未发API请求”为早期状态，已由本记录与既有诊断日志取代。

2026-11-05后续API辅助修订计划：用户提供中科大统一入口`https://api.llm.ustc.edu.cn/`、OpenAI兼容协议及模型ID`deepseek-flash-2`，并确认保持既有设计：80个风险种子补C09/C10/C11，144个种子生成中性背景，普通良性层不新增三条件；先处置六个不接受种子再批量生成。平台公开API指南给出`/v1`基础路径，具体模型ID须通过当前Key的`GET /models`确认，视觉能力仍未核实，不自行改为文档示例模型。辅助生成器不加入四模型评测。

API预检查已由用户在本机PowerShell完成：`GET /models`确认`deepseek-flash-2`列出；普通文本smoke返回同名模型、`finish_reason=stop`；三张随机纯色PNG视觉smoke正确按顺序识别yellow/blue/green，`matched=true`、`finish_reason=stop`，共731 token。该结果只确认OpenAI兼容图片载荷和基础多图读取可用，不证明复杂正式图片的事实提取可靠。正式图片仍需小批事实卡试验与人工核验，不允许据此批量自动认可C09/C10。

六条修订的首个诊断试调用`V3H-DE-11`使用2048最大输出token、120秒超时，结果为`TimeoutError`，无HTTP错误、无响应正文、无candidate，脚本按设计停止且没有自动重试；旧run_id为`repair_diagnosis_fa8581f34559`，失败attempt保留。现将诊断上限降至1024、请求超时提高至300秒，形成新请求哈希和新run_id；旧失败请求不使用`--retry-failed`。正式种子、审校文件仍未修改。

第二次参数化请求使用1024最大输出token、300秒超时，API正常返回同名模型，但`finish_reason=length`，1024个completion token全部计为reasoning token、正文为空；本地标为`generation_not_complete`，未生成candidate，run_id为`repair_diagnosis_8fb6121e25cb`。据此将prompt版本升至`seed-diagnosis/1.1`，诊断恢复2048 token并显式设置`reasoning_effort=low`，保留300秒超时，形成新的请求哈希/run_id。前两次均保留审计记录，不对原请求自动重试，正式数据未改。

已新增`configs/generation/ustc_deepseek_flash2.json`、`scripts/check_ustc_api.py`及`documentation/guides/FORMAL_V3_API_AUTHORING.md`。脚本只支持无网络dry-run、列模型及一句普通连通性问题；不读取数据集、发送图片或使用GPU，不打印Key，不自动重试请求。当前环境没有`USTC_LLM_API_KEY`，只完成dry-run，未发送API请求，也未生成或合入新语段。用户应在其PowerShell终端安全输入环境变量并运行测试，不把Key发到聊天。批量生成与合并脚本尚未实现，需先确认模型ID、图片事实来源和小批输出格式。

生成规范：六条优先回查标签与来源轮次，不将正常防护请求硬改成可执行攻击；C09/C10基于已核验的实验图片事实和插入轮次的可见性，C11基于真实意图转向；每个种子一次生成三条件候选，共80份/240段，再派生配对。背景按seed生成一次并分段复用，不按condition分别随机生成；先选定参考处理器计量口径，CPU测量模板化token，四模型保留同一文本并记录各自实际输入长度。旧背景是按condition轮换十句通用文字，应在候选审定后替换。生成拒绝、截断或无效JSON均记录未完成，不作为操纵有效或通过人工审校的证据。新候选、日志、原数据与A/B审校分开，当前未改数据。

2026-11-05最新人工审校状态：用户已完成A，B由人工校对并与A一致；本次只读审阅确认A为144条决定（138接受、6不接受），其中风险74接受/6不接受，普通良性64全部接受。144个seed_id唯一齐全，来源阅读文件/模板哈希匹配，有效六项审校字段已填。C09/C10/C11三项各144个null，按用户明确指示视为暂缓，后续由用户使用其他模型API辅助生成；本轮不再讨论或改写这些语段，不把null当通过。A/B及阅读稿、模板、种子库均未改动。

六条不接受均为primary：`V3H-PS-07`、`V3H-DE-13`、`V3H-PS-13`、`V3H-DE-11`、`V3H-DE-16`、`V3H-CY-11`。其安全/危险语义配对为5否、1不确定，revision_notes均空；用户提供总体原因“攻击意图不明确”“攻击语句分类排版有问题”，不能未经确认把两类原因逐条代填。原文复核发现部分最终目标更接近防护/科普，DE-11最终请求还与首轮完全重复。当前作为待处置清单，不直接删种子或把标签自动改为安全。旧严格校验器不认识“不接受”，此次仅在派生内存副本中将其解释为reject；未改原始决定。

B JSON仍为144个空决定、身份为空。按用户陈述记录“B人工复核与A一致”，不复制A填入B，不伪造独立盲审身份或计算κ。审阅报告见`documentation/reports/formal_v3_review_round1_20261105.md`，机器报告及输入快照见`outputs/formal_v3_review_checks/review_round1_20261105.json`。当前数据仍4224条、原哈希不变；暂缓三个条件不会自动删除960条轨迹，六个不接受种子的288条轨迹也仍存在。仅作规模估算：暂不使用三个条件为3264条；再排除六种子为3048条，尚未实际执行。下一步处理六条并确定阶段面板、复核/重建/冻结；不能把138接受表述为完整12条件已通过。四模型本次未运行，GPU仍按用户要求不使用。

2026-10-30后续授权与暂停记录：用户允许人工审校前进行探索性运行，但不得代填审校通过；准备了18条校准轨迹的Qwen2.5-VL-7B闸门及带数据/配置哈希的输出清单。18条mock接口流程完成、0失败，仅为模拟接口验证，未产生真实模型安全结果。随后用户要求等待GPU释放，尚未启动真实7B闸门。最新指示是先部署四模型，待用户人工审校完成后再开始模型运行；当前只下载权重、准备接口及普通合成图片诊断，不启动安全数据集实验。

新部署入口为`scripts/prepare_open_models.py`，计划在`configs/deployment/open_models.json`，详情见`documentation/guides/OPEN_MODEL_DEPLOYMENT.md`。Qwen2.5-VL-7B、Qwen3-VL-8B-Instruct、LLaVA-OneVision-7B权重现已完整缓存（分别5、4、4个分片），固定revision，三者均通过离线CPU双图静态/动态预处理和全部历史文本保留检查。修复LLaVA官方模板会静默丢弃字符串形式助手历史的问题，改为结构化文本块；测试59/59通过。GPU生成检查因仅5,681 MiB空闲被门槛阻止，未加载模型；不能把CPU验证通过称为GPU生成通过，更未验证16K资源表现。实际报告在`outputs/model_deployment/*.json`。

Gemma3 12B现已部署到与前三者相同的准备阶段：用户自行取得授权、完成本机HF登录并释放空间后，固定版本`96b6f1eccf38110c56df3a15bffe176da04bfd80`的5个safetensors分片全部下载完成，权重共24,374,793,024字节。离线CPU双图静态/动态预处理均通过，全部用户与助手历史文本保留；合成输入分别553/554 token，两图张量形状均为`[2,3,896,896]`。已按本机Transformers 5.19接口通过`processor_kwargs`传递图片参数，四模型复查全部通过，59/59测试通过。当前四份NF4配置均在`configs/models/deployment/`，全部权重完整，CPU接口就绪，但GPU生成与16K资源表现均未验证。Gemma下载后D盘约余63.87 GiB，本次未使用GPU或启动实验，未改动人工审校文件。无下载队列待续；由用户通知GPU可用及人工审校完成后继续，先串行普通图片生成诊断，再审定数据冻结后的资源闸门和正式评测。四模型计划使用NF4/BF16配置，不能冒充未量化模型结果。

机器构造阶段已经完成：80个危险、64个良性独立来源种子，3,840条危险轨迹和384条良性轨迹，共4,224条；安全/危险配对1,920组，静态/动态配对2,112组，跨种子图片复用为0，目标token最大相对偏差0.195%。完整JSONL为203,907,382字节（约194.46 MiB），SHA-256为`f96688c03415dfcb732230998f26be5d6d7c600cc1bd9c6c8d98a4259649e23e`；种子库SHA-256为`94793582853c1f2bc9423fc307d0e0fc5c4c434f54baf59745c6d71ade7b5dea`。

2026-10-30人工审校发现的待修订问题：C09/C10/C11语段跨场景重复且语义不自然。代码和种子库复核确认，80个有害种子的`redundant_text`、`conflicting_text`、`clarification_turn`各只有1种文本，分别在80个种子中完全复用。当前通用文字分别声明冗余、提示寻找不匹配、要求区分防御与有害用途，不能据此证明实际图文冗余、具体图文矛盾或可信的意图澄清已经成立；还可能额外提示模型关注安全/冲突。至少涉及960条轨迹（80×3条件×2时序×2最终标签），不是960个独立场景。正式冻结前应结合每个种子的实际图片和上下文改写，复核C00关系、最终请求配对和静态/动态文本一致性，保留旧版本与审校来源并重新审定受影响部分。当前只记录问题，未批量修改种子、正式数据、阅读稿或A/B正在填写的文件；不得以模型反应变化代替操纵有效性检查。

所有种子仍明确标记为`machine_constructed_unreviewed`。这表示构建、配额和机器验证完成，不表示人工审校完成。不得在论文中称为“专家审定数据”。

截至2026-10-30，A、B两份JSONL中的144条`decision`仍全部为空，人工审校实际进度为0/288份独立判断。用户自行安排评价填写。已新增两份易填结果JSON，分别继承A/B原有随机顺序，实际判断仍全为空；今后统计进度应优先读取用户实际填写的结果JSON，不能只看未自动回写的源JSONL。

易填结果JSON顶层含`reviewer_code`、留空的`reviewer_id`、原文阅读文件/源模板SHA-256、字段说明和`records`。每条保留`seed_id`和9项判断，填写项允许“是/否/不适用/不确定”，决定允许“接受/修改/拒绝”，未填写用null。人工身份、时间和判断均不自动代填；结果JSON尚未自动导入规范JSONL。后续导入需校验来源哈希、值域、理由与编号，再按seed_id汇总，不能把不适用等同于通过。只有一人填写不能报告为双人盲审。

2026-10-29曾按用户要求清理旧翻译相关内容：本地模型译文、助手直接译文及中间缓存、两份Excel、8张预览图、2份检查记录、独立Markdown阅读稿和对应翻译/Excel/Markdown生成脚本均已删除。英文阅读文件和原始数据保留，2026-10-30按请求另增空白结果JSON用于人工填写。不要恢复已清理的旧Excel或旧译文，也不要代填评价。

2026-10-30用户随后明确授权：把英文阅读文件的自然语言内容使用本地Qwen翻译，另存`formal_v3_readable_original_cn.json`，其余不变。已完成本地缓存Qwen2.5-VL-3B离线翻译，144个场景、2,004处自然语言字段（去重后811段）。5,538处非文本叶字段保持不变，所有图片URL逐字段核对不变，英文源文件SHA-256仍为`f995e9ac714219d830d7922448163a3f923875dd82fa7d0bffbfd22a3ada9a5b`。中文版SHA-256：`4e3597e3720235b7034fbf6a06f38a6ab69ecc79a68adfc84e0770b2feb56940`。无空译文、截断、链接占位残留或替换乱码；语义质量未人工审定。新文件只辅助阅读，不改变正式数据或A/B审校来源哈希。元信息按用户要求继承英文输入，独立翻译验证报告在`outputs/formal_v3_cn_translation/verification.json`。

原种子只选取部分来源图片，13个良性场景的原文图片编号曾超出当前保留数量。本次仅对阅读辅助文件按原始MMDU图片数组、MMDS用户图片首次出现顺序建立完整参考图片映射，并以`included_in_experiment_evidence`区分是否进入当前实验。未改变正式数据集的证据选择；后续仍需人工核对语义和编号，不能把图片文件存在等同于样本语义审定。

英文阅读JSON验收：144个唯一seed_id（风险80、良性64），623个来源图片链接均存在，406处显式编号占位符已替换，剩余占位符为0；题干除链接替换外未变，种子库、正式JSONL、A/B审校表哈希前后相同。阅读文件SHA-256：`f995e9ac714219d830d7922448163a3f923875dd82fa7d0bffbfd22a3ada9a5b`。

2026-10-30新增只读审校检查工具和10项内存中合成测试，全套测试54/54通过。覆盖中文/英文/布尔选项、缺失/重复编号、部分完成、不适用、不确定、理由缺失、接受矛盾、同人不能算双人、逐seed配对、κ无定义和输入不变。当前检查无格式错误、完整决定仍为0/288，空白不计作一致。检查报告位于`outputs/formal_v3_review_checks/`，不写入或改动正在填写的A/B文件。

`formal_v1`上次验证为456条、212组配对，`formal_v2`上次验证为1,554条且MMDS/MMDU独立来源数分别为192/110。规范分片连续两次重建后`manifest.json`的SHA-256均为`c225c3a00201c8ee3555042bbe421d117e324fd416b1333f5fecd66bc29c3ab9`，压缩分片构建具有确定性。

下一步顺序：

可与人工审校并行推进只读工具、分析方案、模型接口/版本核对和独立良性诊断准备；当前未启动新正式推理、未下载模型。不得在用户审校期间重新生成或覆盖结果文件、修改现有题干/编号或泄漏另一位审校者的判断。正式全量实验仍需下列步骤完成。

1. 对144个种子进行人工双人审校；
2. 优先复核图片事实描述、机器分配的良性子类型和跨源子类型映射；
3. 复核安全/危险请求的语义对等及`C09/C10/C11`自然度；
4. 仲裁分歧并生成审定版种子库；
5. 重新构建、验证和冻结审定版哈希；
6. 然后再为四个计划模型建立全新的运行适配与配置。

不得用自动改写姓名、地点和数字扩充独立场景；不得用复制、裁剪或颜色变化把一张图伪造成多个独立证据；不得把未经双人审校的弱标签当作真实风险分数。

## 8. 工作区清理说明

2026-10-30 Gemma曾因磁盘保留空间规则返回`waiting_for_disk`。用户随后清理空间，该阻塞已解决，5个权重分片与CPU接口检查均已完成，详见第7节。无需重复授权或登录，不将授权token写入文档。

2026-10-23已停止旧模型实验路线并清理：

- `outputs/`中的旧推理、标注和指标目录；
- `configs/runs/`中的旧实验运行配置；
- 旧0.5B/3B/SmolVLM2临时模型配置与适配增量；
- 旧闸门、烟雾测试和模型就绪报告。

保留内容包括数据源、数据种子、`pilot/formal_v1/v2`数据、数据构建和验证脚本，以及可供后续重建实验能力的通用代码。当前不要恢复旧运行队列。

## 9. 接手提示

新对话先读文首“最新交接摘要”与本地`outputs/formal_v3_18turn_runs/queue_status.json`，核对进程、锁、g1024运行配置及数据/代码指纹，再检查Git状态。18轮4864条已完成重建和验证；本地只继续Qwen并在完成后暂停检查，云端3090则准备LLaVA/Gemma，不得恢复原四模型自动接续。不要重建活动运行输入、并行加载第二个模型、恢复旧512队列或混计gate/formal。不要重新生成旧A/B或废弃六条改写。若中断只恢复授权的当前单模型，重新落实完成后暂停；推理实现/参数变化须新运行版本。云端下载先核对用户回传的子进程与锁，不凭历史PID删除锁或kill。模型回答标注仍待后续推进。


## RTX3090云端独立方案补充（2026-11-06，最新云端选择）

用户将云GPU改为单张RTX3090 24GB，镜像为Ubuntu22.04/Python3.12/PyTorch2.12.1/CUDA13.0，CPU为14 vCPU Xeon Gold6330。新增独立入口`scripts/cloud_experiment_rtx3090.sh`、`scripts/cloud_runtime_rtx3090.py`、`configs/cloud/rtx3090_llava_gemma.json`、版本约束及`requirements-cloud-rtx3090.txt`，原4090部署脚本/配置/依赖/指南均未改变。新入口在`.cache/venvs/rtx3090`创建继承镜像Torch的独立环境，约束torch2.12.1及官方对应torchvision0.27.1，不改变基础镜像、不自动改驱动。主要推理包保留原锁定版本，GPU/BF16实际操作和依赖检查须在云端执行。

默认LLaVA-OneVision-7B→Gemma3-12B-IT，每模型16条gate后4864条formal，共9728条formal。保持相同冻结数据、模型revision、NF4/BF16、SDPA、固定参考历史和1024输出预算；新run_id后缀`-rtx3090-t2121-py312`，结果位于`outputs/cloud_rtx3090_runs`，配置及环境记录分别为`outputs/cloud_rtx3090_configs`和`outputs/cloud_rtx3090_environment`。控制状态、日志、CPU面板与互斥锁仍复用`outputs/formal_v3_18turn_runs`；同一工作副本不同时启动新旧入口。本地Qwen继续、完成后暂停检查的安排不变，Qwen3不由此入口启动。

本地已验证82项测试通过、Bash语法通过；逐字核对旧云端入口/依赖/manifest/指南无变化，新计划只选LLaVA与Gemma，保留所有冻结实验控制项，环境或既有配置不符时拒绝运行。尚未在云服务器安装、下载或进行3090推理，不宣称GPU闸门已通过。操作说明见`documentation/guides/CLOUD_RTX3090_EXPERIMENT.md`。Gemma需在云机以获批账号单独HF登录；不得上传本机token。不同硬件/Python/Torch环境有数值差异，保留运行来源，未完成人工回答评价前不报告ASR/安全率。


### RTX3090云端下载诊断补充（2026-11-06）

用户云端已实际通过Python3.12.3、torch2.12.1+cu130、torchvision0.27.1+cu130、RTX3090和BF16矩阵检查；LLaVA下载config.json时报告TypeError，未进入权重加载或推理。现有报告仅保留异常类型，不能据此认定网络、授权或依赖为根因。新增scripts/diagnose_hf_download.py，仅请求固定revision的config.json，记录脱敏错误信息、调用帧、异常链HTTP状态及HTTP/进度条依赖版本；可用--disable-progress做第二次对照，不更改模型或实验配置，不请求权重、不用GPU。诊断及脱敏2项测试通过，需用户在云端运行并回传脱敏输出后定位具体原因。


### 云端下载TypeError根因与修复（2026-11-06）

用户回传完整诊断：HF2.2.0/httpx2与httpcore2均2.16.0，错误在httpx2._decoders.decode第191行，`process() takes no keyword arguments`；与上游httpx2#1296所述旧Brotli不支持`output_buffer_limit`接口完全匹配。3090专用requirements新增Brotli==1.2.0；新scripts/check_http_download.py离线压缩/解压真实小文本校验HTTP decoder，3090环境检查调用此校验，诊断脚本增加Brotli/brotlicffi版本。原4090依赖和冻结推理代码/数据不修改。修复在隔离缓存目录安装Brotli1.2.0后用本地HTTP decoder往返验证通过；还需用户在云端虚拟环境升级这一下载依赖并复测小文件，未宣称云端模型下载完成。无需重装Torch/CUDA、降级HF或清空权重缓存。


### 每30分钟本地Qwen进度检查（2026-11-07）

用户明确要求定时检查，已通过应用工具创建本对话heartbeat，ID `30-qwen`，ACTIVE，每30分钟检查本地Qwen正式run；不另建操作系统计划任务。读取状态及实际结果数量、错误、写入时间/进程和技术指标，与`outputs/formal_v3_18turn_runs/scheduled_qwen_progress.json`快照比较。仅检查记录，不自动启动/恢复/停止模型，不接续其他模型，不碰云端任务；用户暂停优先。初始快照1806/4864、错误0、状态`running`。定时任务已实际创建，勿重复创建；更改时先定位并更新此ID。
