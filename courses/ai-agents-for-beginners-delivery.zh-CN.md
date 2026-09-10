# AI 智能体课程 zh-CN 交付说明

## 当前状态

本次交付将真实源课程 **00 环境准备和 01–18 全部正式模块**适配为独立平台阅读包，保留原始课程、示例、notebook 和其他语言的现有用途。不是一个 Hello World 演示包，也没有把平台阅读器当成执行环境。

**内容适配与供应方静态自检，不等于平台正式校验、教学验收或发布。** 当前没有完整的官方 v1 平台校验工程；全部教学路线仍为待演练。没有执行云资源部署、真实模型调用、生产账号登录、邀请发送或平台内容上传。Git 提交和推送由后续获授权的 PR 流程处理，创建 PR 不等于发布验收。

## 交付定位与版本

| 项目 | 本次实际信息 |
| --- | --- |
| 仓库 | `https://github.com/deepenable/ai-agents-for-beginners` |
| 课程根目录（相对仓库） | `courses/ai-agents-for-beginners` |
| 课程清单 | `courses/ai-agents-for-beginners/course.json` |
| 课程 ID | `ai-agents-for-beginners`；首次导入前由接收方确认无冲突并约定，之后保持稳定 |
| 实验 ID | `lesson-00` 到 `lesson-18`，按源课程顺序 |
| 章节 ID | 00 为 `lesson-00-overview`、`lesson-00-setup`、`lesson-00-license`；01–18 为 `lesson-NN-concepts` 和 `lesson-NN-practice` |
| 交付语言 | 仅 `zh-CN`；也是默认语言，所有标题、简介和章节映射均完整 |
| 输入源码版本 | `25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595`；已通过 fork 的 GitHub commit API 确认存在 |
| 最终发布 40 位提交 | **由接收方从包含本交付包的实际 PR 提交中选定并记录**。输入源码提交不包含本次新增交付包，不能用作最终导入快照 |
| 平台资源要求 | 所有 `requires` 为 `[]`；不要求平台分发凭据或 Copilot 邀请 |
| 联系人 | 用户未提供经确认的交付/接收联系人；由双方在交接工单补充，不使用上游作者或机器人身份代填 |
| 仓库读取授权 | 由接收方按实际仓库可见性验证；若需要私有仓库读取授权，通过约定安全渠道配置，不写入清单或手册 |

依据本次收到的只读《实验手册交付规范 v1》编写。其示例课程与资源领取包引用文件未随协议提供，未据此声称这些材料或官方验证器已存在。

所读协议文件的 SHA-256 为 `00d0d81496017a4c44c2318d1ee868ad108b9bef0deb5890c8861355595c002b`，仅用于识别本次约束来源，未修改协议来源目录。

## 模块与章节覆盖

清单包含 **19 个实验、39 个独立简体中文章节**。00 有学习路线、环境准备、来源许可三章；01–18 各有概念和实践两章。教学主体重新组织为中文讲解、真实代码操作、预期判据、故障处理和清理；源码只通过固定版本普通 HTTPS 链接提供，不作为未声明附件塞入包。

本次供应方检查得到以下实际统计；大小均按未压缩文件字节计算，只统计清单及声明内容，不把外部交付说明和报告算入课程包：

| 指标 | 实际值 | v1 上限 |
| --- | --- | --- |
| 实验 / 章节 / 图片 | 19 / 39 / 11 | 不单列上限 |
| 声明文件数（含清单） | 51 | 200 |
| 声明文件总字节数 | 1,972,755（约 1.88 MiB） | 26,214,400 |
| 清单字节数 | 9,128 | 65,536 |
| 最大 Markdown 字节数 | 22,644 | 262,144 |
| 最大图片字节数 | 224,427 | 2,097,152 |

交付文本使用 Git 保存的 LF 换行；上述字节数及报告摘要按相同换行计算，避免 Windows CRLF 工作副本与提交快照不一致。

| 源模块 | 教学内容与真实示例路线 | 本地章节文件前缀 | 教学演练 |
| --- | --- | --- | --- |
| `00-course-setup` | 固定源码、Python/内核、Foundry/OpenAI 身份配置、可选资源与版本边界 | `00-overview` / `00-setup` / `00-license` | 待演练 |
| `01-intro-to-ai-agents` | 智能体组成、适用场景、旅行助手与工具循环 | `01-concepts` / `01-practice` | 待演练 |
| `02-explore-agentic-frameworks` | 框架边界、Foundry 项目与直接 Azure OpenAI 接入 | `02-concepts` / `02-practice` | 待演练 |
| `03-agentic-design-patterns` | 智能体交互原则、任务边界和可理解行为 | `03-concepts` / `03-practice` | 待演练 |
| `04-tool-use` | 工具声明、函数参数、旅行工具、输入校验与副作用 | `04-concepts` / `04-practice` | 待演练 |
| `05-agentic-rag` | 检索证据、内存知识库、可选真实搜索索引及 .NET 路线 | `05-concepts` / `05-practice` | 待演练 |
| `06-building-trustworthy-agents` | 系统消息、威胁边界、人类监督和审批 | `06-concepts` / `06-practice` | 待演练 |
| `07-planning-design` | 目标分解、结构化计划、任务执行和再规划 | `07-concepts` / `07-practice` | 待演练 |
| `08-multi-agent` | 协作、交接、顺序/并发/条件工作流、Bing 拓展、.NET 对照 | `08-concepts` / `08-practice` | 待演练 |
| `09-metacognition` | 自评、反思、修订及外部评价边界 | `09-concepts` / `09-practice` | 待演练 |
| `10-ai-agents-production` | 评估、可观测性、质量门禁、费用报销补充示例 | `10-concepts` / `10-practice` | 待演练 |
| `11-agentic-protocols` | MCP、A2A、NLWeb、真实客户端/服务端、GitHub MCP 拓展 | `11-concepts` / `11-practice` | 待演练 |
| `12-context-engineering` | 上下文选择/压缩/隔离、摘要和 scratchpad | `12-concepts` / `12-practice` | 待演练 |
| `13-agent-memory` | 记忆类型、持久化、检索、遗忘和 Cognee 可选路线 | `13-concepts` / `13-practice` | 待演练 |
| `14-microsoft-agent-framework` | 六种框架 notebook、酒店流程、托管代理补充代码 | `14-concepts` / `14-practice` | 待演练 |
| `15-browser-use` | 浏览器感知、动作规划、受控任务与网页安全边界 | `15-concepts` / `15-practice` | 待演练 |
| `16-deploying-scalable-agents` | 部署形态、生命周期、路由/缓存、评估/HITL、遥测和冒烟门禁 | `16-concepts` / `16-practice` | 待演练 |
| `17-creating-local-ai-agents` | Foundry Local、沙箱工具、本地 RAG/MCP、混合路由 | `17-concepts` / `17-practice` | 待演练 |
| `18-securing-ai-agents` | 签名回执、规范化、篡改/链验证和人工授权回执 | `18-concepts` / `18-practice` | 待演练 |

上述前缀均位于课程根 `chapters/`，扩展名为 `.zh-CN.md`。机器可读的源模块、notebook 变体链接覆盖及逐文件字节数、SHA-256 摘要保存在[供应方自检报告](ai-agents-for-beginners-supplier-check.json)中。原始主课源目录含 38 个 notebook，其中 33 个 Python、5 个 .NET；旧名称中出现 `ghmodel` 不证明它仍使用 GitHub Models。

## 资源与执行边界

| 范围 | 自备资源与注意事项 |
| --- | --- |
| 通用主线 | Windows 11 / PowerShell 7 / Python 3.12+ / Git / Python notebook 编辑器；`requirements.txt` 约束的 MAF 1.10 系列；Azure CLI 与获批准的开发订阅 |
| Foundry/直接 OpenAI | 实际项目端点或 Azure OpenAI 端点、部署名、兼容 API/模型、数据权限、配额和预算；不是所有示例都使用同一个客户端或认证链 |
| 05/16 Search | 内存检索主线无需另建 Search。可选索引路线单独计费；16 当前需端点与 API key 同时配置才走真实 Search，不能声称其已经实现无密钥 Search |
| 08/11 外部工具 | Bing 连接、GitHub MCP 所需的最小只读权限按具体路线申请；不发平台邀请，不授予真实仓库写入权限作演示 |
| 13/14 补充后端 | Cognee、其他模型供应商或 hosted 示例可能需要额外依赖和外部服务；必须按源码确认，不能视为通用环境已包含 |
| 15 浏览器 | 独立浏览器环境与下载、获授权的目标页面；页面数据可能发送到模型，避免登录态、个人账号和真实交易 |
| 17 本地 | Foundry Local、兼容模型和足够设备内存/磁盘；首次下载需要联网，某些模型/嵌入也可能额外下载；本地部署不保证任意模型都支持工具调用 |
| 18 回执 | 可先用本地加密依赖和合成数据验证；签名证明完整性/来源而非模型结论正确，不复用实验密钥到生产 |

`requires: []` 只表示没有必须由平台分发的能力，不表示无需资源或免费。云服务、外部 API、Search、存储、网络、浏览器模型调用及 Codespaces 可能收费，已在手册中醒目标明。受控项目的数据角色应由管理员按最小范围配置；禁止用扩大到订阅 Owner 的办法跳过权限排查。

所有真实端点、密钥和令牌只保存在学习者自己的安全环境。本包不附 `.env`、邀请、真实资源 ID、个人截图或生产凭据。源码中的环境文件样例可能带非空 `...`，手册明确要求只填写真正使用的变量，避免误选可选服务分支。

## 规范适配与维护策略

清单严格保留 v1 字段，交付元信息在本文件，不放入 `course.json`。不填写未经估计的 `durationMinutes`。标题可调整，已发布 ID 不应随标题漂移。

各章只有一个描述性 H1，用 H2/H3 编排教学。不导入源仓库语言菜单、徽章、贡献说明、邀请信息、手写目录、HTML 锚点或嵌入页面。代码中的 HTML/本机 HTTP 地址仅作为代码文本。源码保留固定版本 HTTPS 普通链接；本地链接仅指向清单声明的章节或图片。

图片使用真实普通文件并在 `assets` 声明；不使用远程图片、SVG、账户截图、符号链接、junction、硬链接、子模块或 LFS。必要机构版权保留；[已声明的许可章节](ai-agents-for-beginners/chapters/00-license.zh-CN.md)包含完整原始 MIT 文本，保证平台导入后仍携带许可。

### 图片来源

下表源路径均相对于仓库，属于前述真实输入提交。图片是原课程示意图，不是本次运行截图；部分原图含英文标签，章节中文正文说明其概念与边界。保留来源和机构许可，不另行声称取得了产品商标背书。

| 交付 `assets/` 文件 | 原始素材路径 |
| --- | --- |
| `01-agent-components.webp` | `translated_images/zh-CN/what-are-ai-agents.1ec8c4d548af601a.webp` |
| `04-function-calling.png` | `04-tool-use/images/functioncalling-diagram.png` |
| `05-self-correction.png` | `05-agentic-rag/images/self-correction.png` |
| `06-system-message-framework.png` | `06-building-trustworthy-agents/images/system-message-framework.png` |
| `07-goals-and-tasks.png` | `07-planning-design/images/defining-goals-tasks.png` |
| `08-agent-handoff.png` | `08-multi-agent/images/multi-agent-hand-off.png` |
| `09-rag-and-context.png` | `09-metacognition/images/rag-vs-context.png` |
| `11-a2a-travel.png` | `11-agentic-protocols/images/A2A-Diagram.png` |
| `11-mcp-travel.png` | `11-agentic-protocols/images/mcp-diagram.png` |
| `12-context-types.png` | `12-context-engineering/images/context-types.png` |
| `14-agent-components.png` | `14-microsoft-agent-framework/images/agent-components.png` |

已对照固定 Git 对象核实 11 张来源。10 张 PNG 经 Pillow 12.3.0 去除 Adobe XMP 等非必要附加元数据，逐张确认尺寸与解码 RGBA 像素不变；WebP 与源文件逐字节一致。这样避免把制图工具的附加身份信息复制进包，不删改图中文字、机构署名或 MIT 许可。

需要重复清理时，从上述原图普通复制到目标路径，再对 PNG 执行如下等价操作，最后重跑自检；这里的 `image_path` 必须是已确认归属的具体交付 PNG 路径，不允许指向原图：

```python
from PIL import Image

with Image.open(image_path) as source:
    pixels = source.convert("RGBA").tobytes()
    clean = source.copy()
clean.info.clear()
clean.save(image_path, format="PNG", optimize=True)
with Image.open(image_path) as result:
    assert result.convert("RGBA").tobytes() == pixels
```

课程文字为逐章对照源码整理的适配，不依赖无法重现的一次性批量替换。更新源版本时，用报告中的逐模块源链接与 notebook 覆盖对照实际代码，检查 API、认证、工具副作用、相对路径、可选配置分支和清理行为，再更新固定链接与检查脚本的 `SOURCE_SHA`。不要把过期中文翻译中的配置假设机械复制回来。

## 已识别的源码与环境差异

这些问题已在对应手册给出隔离练习、学习副本修正或明确的停止条件；**原始源文件保持不变**，因此不能声称原仓库所有示例无需修改即可运行。

| 模块 | 演练前必须注意的差异 |
| --- | --- |
| 01–05 | 跳过 notebook 未约束安装单元格；02 文档与实际 `as_agent` 有差异；03 有指令要求但缺库存工具；04 结构化段漏传格式，手册给出补充调用；05 月份缩写/空查询边界与旧 .NET 上传清理风险均单列 |
| 06–08 | 06 演示门禁仍会调用提案模型，审批不执行真实业务；07 依赖顺序主要靠提示；08 条件 Python/.NET 变体保留旧 API、Bing 绑定/清理限制，不应混装升级主环境 |
| 09–10 | 09 原 notebook 覆盖响应变量导致评估问题与答案错配，手册给出具名变量修正；10 报销解析可能跳过无效明细，且未实现发信、附件、饼图或真实遥测；只允许合成收据 |
| 11–12 | 主协议 notebook 是进程内模拟，不证明远程 MCP/A2A；真实 MCP 客户端有恢复限制，审批异常继续模拟执行；Chainlit 集成未把工具接入智能体且导入即可能写 Search；12 摘要工具不自动裁剪历史或写便签 |
| 13–14 | 13 字典不持久，两种记忆路线有工具注册缺口，Cognee 有额外提供商和删除风险；14 顺序/并发输出模式需明确绑定、handoff 集成依赖待确认，旧酒店脚本另有 API 差异 |
| 15–16 | 浏览器库未完全锁定且存在重复类定义，手册选最后生效路径；16 没有真实 hosted 运行时部署、完整审批恢复或持久化，缓存原键不隔离客户，评估与 smoke 断言不等于安全认证 |
| 17–18 | 17 默认 Chroma 为内存库、MCP 示例仅列工具，推理及嵌入可能首次下载；18 的直接 JCS 签名不能沿用旧翻译预哈希，内存防重放/嵌入公钥/模拟时间均不是生产保证 |

未锁定的浏览器、.NET 预览包、orchestrations、Cognee 与 hosting 组合需由接收方在声明环境中建立实际兼容版本记录。手册中的修改片段是明确的教学扩展，不伪装为上游已经实现或已实际验证的能力。

## 本地供应方检查记录

本次新增 `scripts/check_lab_delivery.py`，命名和输出均明确是**供应方针对性检查，不是官方平台验证器**。它离线检查本包使用的 Markdown 子集，不保证覆盖 CommonMark 的所有扩展或平台内部渲染差异；它不执行 notebook、不访问云端，也不检测外部文档的在线可用性。

检查范围包括：JSON 重复键和额外字段、必需语言/ID/数组约束、声明数量及字节上限、精确大小写/ASCII 路径、课程根祖先及文件类型、未声明文件、链接/锚点/HTML、图片格式签名与实际解码、LFS/子模块、源码链接在固定 Git 树内存在、19 模块顺序及全部 notebook 变体有来源链接。图片的教学意义和敏感信息仍需人工复核，不能由签名检查推出安全结论。

在仓库根复现：

```powershell
python -m unittest discover -s scripts -p test_check_lab_delivery.py
python .\scripts\check_lab_delivery.py .\courses\ai-agents-for-beginners --report .\courses\ai-agents-for-beginners-supplier-check.json
.\scripts\validate-notebooks.ps1 -Python python -List
git diff --check
```

自检需要 Pillow（源课程已列入依赖）；现有 notebook 清单命令也需要 nbconvert。此次缺少这些包后，在会话产物目录的独立虚拟环境安装了 Pillow 和 nbconvert，没有修改共享系统 Python 或课程依赖。实际调用命令中的 `python` / `-Python python` 使用该隔离解释器的绝对路径。

供应方检查日期：**2026-09-10**。实际检查机器为 Windows，PowerShell **7.6.6**、Python **3.11.2**、Pillow **12.3.0**、nbconvert **7.17.1**。这里的 Python 3.11 仅用于离线供应方核查；**不满足课程声明的 Python 3.12+ 教学环境，不构成课程可运行的证据**。完整教学 OS/工具组合、执行日期、实际输出、配额与问题恢复均待演练后填写。

现有 `validate-notebooks.ps1 -List` 已实际列出 33 个 Python notebook，未运行代码；输出提示未配置 `.env`/Foundry 端点，符合本次不使用云账号的边界。没有执行省略 `-List` 的批量调用，也没有把列表结果标成 notebook PASS。

供应方检查器的 19 个回归用例已通过，涵盖重复 JSON 字段、非法 schema 类型、ID/路径冲突、数量上限、HTML 与代码区分、链接/锚点、图片真实格式、硬链接和 URL 凭据等故障样例；这些是新增本地工具自身的用例，不是官方平台的测试。

还分别使用 Python `compile(..., ast.PyCF_ONLY_AST | ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)` 和 PowerShell `System.Management.Automation.Language.Parser.ParseInput` 对正文中的 **100 段 Python 围栏、65 段 PowerShell 围栏**做语法解析，均无语法错误。解析不会运行命令，不证明 SDK 接口、服务或教学结果可用。

另在隔离的临时目录，以同一 Python 3.11.2 解释器执行了 16 的纯规则/假代理关卡与模拟审批片段、17 的受限文件工具与 TODO 定位片段，四段均通过内置断言。只复制所需固定源码 notebook 供 AST 白名单提取，未执行客户端、模型或 Chroma 初始化。这是补充的离线片段核查；不代表这些模块在 Python 3.12+ 目标环境中的完整教学演练已通过，云端和本地模型路线仍待演练。

自检的最新数值与错误列表以同目录生成报告为准；每次内容变更后需重新生成，报告内含每个声明文件的 SHA-256，可用于识别报告过期，但不是最终 Git 提交或签名验收凭证。

整包命令实际退出码为 **0**，报告为 `supplierChecksPassed: true`、`errors: []`；19 个模块的 README 与 38 个原始 notebook 来源全部覆盖。报告同时明确 `officialValidation: not-run` 和 `teachingRehearsal: pending`。`git diff --check` 退出码为 0。没有执行或伪报协议中的官方命令。

## 尚需接收方完成的交接

1. 确认课程 ID 与现有平台无冲突，约定后冻结；填写交付方和接收方联系人，确认仓库只读访问方式。不使用源作者、机构公共邮箱或本次代理名字代填联系人。
2. 在用户授权下将实际改动提交到 Git，取得**包含此包的真实 40 位 commit**。当前输入 SHA 不包含此包，禁止复制到“最终发布提交”字段。将同一最终提交提供给校验、预览和教学抽验。
3. 取得与《实验手册交付规范 v1》匹配的完整平台工程，记录其版本。在那个工程的根目录执行协议命令，而不是在本课程仓库运行不存在的脚本：

```powershell
npm ci
node --import tsx -- scripts/validate-course.ts "D:\supplier\ai-agents-for-beginners\courses\ai-agents-for-beginners"
```

上面的路径须换成接收方**最终提交检出**里的实际课程根；Node.js 22 LTS 为协议要求。命令在本次未执行，未声称得到官方 `"valid": true`。

4. 对每个实验在声明环境中演练，记录实际日期、OS、Python/.NET/浏览器/CLI/SDK、具体模型与服务配置、运行步骤、去敏结果、失败与恢复、费用/权限及资源清理结果。每个可选路线单独记录执行或未执行；不能以主线成功代替全部拓展通过。
5. 预览导入后的 39 章导航、中文标题、代码复制、图片和锚点，确认当地环境的真实资源/身份配置。人工验收教学质量后再由接收方发布；导入成功本身不是发布完成。

未演练的字段保留“未执行/待演练”，不得事后补写虚构的时间、版本、输出或截图。如果发现源示例因 SDK 演进不能运行，先记录阻断点和实际修正，再交付新的真实提交；不把不成功的路径描述为已经验证。
