# 实践工具发现、旅行协作与可恢复 MCP

## 目标与前置条件

本章先运行两个 Python 教学 notebook，观察住宿工具与三智能体顺序协作，再把真正的本机 MCP 服务作为可选路线。最终应能提交“调用了什么、在哪一层运行、哪些能力尚未实现”的证据，而不只是聊天截图。

先完成[环境准备](00-setup.zh-CN.md)和[协议概念](11-concepts.zh-CN.md)。使用 Windows、PowerShell 7、Python 3.12+；根依赖固定 `agent-framework-core==1.10.0`，Foundry/OpenAI 集成遵守根清单约束。notebook 自带的 `%pip install agent-framework ...` 没有相同约束，应跳过，不能用它覆盖课程环境。

### 开始操作前的费用、权限与删除风险

- 两个 notebook 的工具和分工是模拟的，但 `FoundryChatClient` 的推理是真实收费调用；需要已批准的 Foundry 项目、支持工具调用的模型部署及项目范围调用/智能体管理权限。
- 主线使用 `DefaultAzureCredential`，不保证最终选择 Azure CLI 身份。按环境准备核对实际凭据链，不打印令牌。
- 本地 MCP 变体只使用模拟数据，research sampling 也是固定文字，不需要 Azure 或 GitHub 令牌；不要把监听地址改成公网网卡，也不要把恢复令牌上传。
- GitHub/Chainlit 扩展会访问外部服务并在导入时修改 Search 数据，本章只做静态追踪。它不属于安全的“先启动再看看”路线。
- 所有“价格”“预订成功”“退款”均为课程模拟。不要替换成实际扣款工具，更不要沿用自动批准配置。

## 步骤一：准备副本与核对版本

工作目录为源码仓库根。使用 VS Code/Jupyter 的 `.venv` 内核；以下复制只创建自己的练习文件。若 `lab-work\11` 已有内容，先检查，不覆盖既有作业。

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
New-Item -ItemType Directory -Force .\lab-work\11 | Out-Null
Copy-Item .\11-agentic-protocols\code_samples\11-mcp-agent-framework.ipynb .\lab-work\11\11-mcp.ipynb
Copy-Item .\11-agentic-protocols\code_samples\11-a2a-agent-framework.ipynb .\lab-work\11\11-a2a.ipynb
```

预期 SHA 为 `25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595`，核心包为 `1.10.0`。复制不是执行。以下“单元格号”按原文件从 1 开始计数，包含 Markdown；修改副本后以函数或章节名定位。

来源：[MCP notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/11-mcp-agent-framework.ipynb)、[A2A notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/11-a2a-agent-framework.ipynb)。

## 步骤二：把 MCP 模式与真正 MCP 分开验证

### 先读工具，再允许模型使用

打开 MCP 副本。跳过单元格 3 的安装；运行导入与配置单元格 4 前，确认只配置了环境准备要求的两个 Foundry 变量。单元格 8 定义：

- `search_accommodations(location, check_in, check_out, guests=2)`：从内置字典返回 Tokyo、Paris、Barcelona 的住宿。
- `get_local_experiences(location, interest="all")`：从 Tokyo、Paris 的活动表返回餐饮、文化等条目。

两者用 `@tool(approval_mode="never_require")` 注册。这里“无需审批”只适合这些没有真实写操作的模拟函数，不应推广至订房、购买或个人数据写入。

工具并不核验日期、入住资格或房态；`location` 的查找区分大小写，`Tokyo` 有结果而 `tokyo` 没有。`interest` 不存在时会回退全部类别，而不是报错。列出的美元价格是静态示例，不是实时报价。

### 运行一次明确输入

单元格 10 创建 `AccommodationAgent`，并在 `tools=[search_accommodations, get_local_experiences]` 中显式传入工具。将副本中的原始模糊月份请求改为下面的合成请求，然后执行一次：

```python
response = await agent.run(
    "Use search_accommodations for Tokyo, check_in 2027-04-10, "
    "check_out 2027-04-15, guests 2. Then use get_local_experiences "
    "for Tokyo with interest culture. Compare choices; do not book anything."
)
print(response)
```

这是替换原有调用，不是在不创建 `agent` 的空内核中独立运行。预期回答有东京住宿与文化活动，住宿候选来自三条固定记录，不能声称已经预订。

为了判断工具确实被调用，可在**副本**两个函数体开头各加入 `print("called: search_accommodations")` 或 `print("called: get_local_experiences")`，重新执行工具定义和创建智能体单元格，再发一次请求。只打印名称，不打印用户输入或凭据。

合格证据包含两个调用名称、返回条目与回答的对应关系，以及“未创建 MCP 连接”。若只看到自然语言回答而没有调用证据，不能给工具使用记通过。

### 一个边界反例

把城市改为 `Atlantis`，预期工具返回无记录。模型应承认无数据，而不是编造住宿；即使模型提议其他城市，也必须区分建议与工具已返回事实。这同时检验了数据接地与未知结果处理。

## 步骤三：运行 A2A 风格的进程内旅行协作

打开 A2A 副本并重启独立内核，避免误用前一个 notebook 的变量。跳过单元格 3，顺序执行 4、5、8。三个智能体共用同一个 `FoundryChatClient`：

| 名称 | 职责 | 并未具备的能力 |
| --- | --- | --- |
| `CurrencyExchangeAgent` | 货币与换汇建议 | 没有实时汇率工具 |
| `ActivityPlannerAgent` | 景点、文化、餐饮建议 | 没有外部目录检索 |
| `TravelManagerAgent` | 整合旅行简报 | 没有真正预订工具 |

单元格 10 的关键代码是：

```python
workflow = WorkflowBuilder(start_executor=currency_agent) \
    .add_edge(currency_agent, activity_agent) \
    .add_edge(activity_agent, travel_manager) \
    .build()
```

读完后运行原始 Tokyo 请求。它以 `workflow.run(..., stream=True)` 返回事件，界面只打印 `event.type == "output"` 且数据为 `AgentResponseUpdate` 的内容。过滤器可能漏掉其他事件类型，空白界面不能直接证明工作流没执行。

在副本的事件循环中临时加入 `print(event.type)` 可排查类型；不要记录完整生产请求。若需要检查已批准的一次新调用，可另外使用非流式运行并检查 `events.get_outputs()`，注意这会重新产生模型费用，而不是免费读取上次结果。

预期结果是旅行简报，包含货币注意事项和活动建议。还应检查：

1. 经理是否收到并保留原始兴趣，而不是只重复上一个专家的话。
2. 汇率是否标明未实时验证；没有查价工具时不能把具体数值当作当日报价。
3. 代码是否出现远程 A2A 端点、Agent Card 或 JSON-RPC 任务交互。这里没有，记录为“进程内模拟通过/失败”，不写“A2A 互联通过”。

## 可选路线一：真正的本机 MCP 服务与客户端

### 准备服务依赖和工作目录

来源：[服务端](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/mcp-agents/server/server.py)、[交互客户端](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/mcp-agents/client/client.py)、[恢复客户端](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/mcp-agents/client/resumable_client.py)。

需要 `mcp[cli]`、`anyio`、`starlette`、`uvicorn`、`pydantic`、`rich`；部分由根依赖间接安装。先在源码根检查，不运行服务：

```powershell
.\.venv\Scripts\python.exe -c "import mcp, anyio, starlette, uvicorn, pydantic, rich; from importlib.metadata import version; print({n:version(n) for n in ['mcp','starlette','uvicorn','pydantic','rich']})"
```

缺少依赖时只在课程虚拟环境补装缺项，并记录实际解析版本。MCP 版本未由源项目完全锁定；若签名与 `ClientMessageMetadata` 等 API 不兼容，先停止并保留错误，不盲目升级核心框架。

两个 PowerShell 终端均从源码根进入同一子目录。服务器仅绑定回环地址，勿对公网开放：

```powershell
Set-Location .\11-agentic-protocols\code_samples\mcp-agents
..\..\..\.venv\Scripts\python.exe -m server.server --port 8006
```

另一终端：

```powershell
Set-Location .\11-agentic-protocols\code_samples\mcp-agents
..\..\..\.venv\Scripts\python.exe -m client.client --url http://127.0.0.1:8006/mcp
```

预期完成 `initialize()`，显示工具 `travel_agent`、`research_agent`、`long_running_agent`。这些才是真正经过 MCP 发现的工具。不要用普通浏览器 GET 返回 405 等现象判定协议失败；端点需要正确的 MCP 请求。

### 逐个检验交互能力

1. 输入 `list`，核对三种工具。
2. 输入 `travel_agent`，目的地填 `Paris`。在价格询问时输入 `n`，原因填合成文字 `lab decline`。预期出现取消结果，而非成功预订。
3. 再运行一次同工具并接受，预期出现模拟成功文字；没有航空公司 API，因此不是实际交易。
4. 输入 `research_agent`，主题填 `MCP teaching demo`。预期出现 sampling 提示及客户端的固定模拟摘要。记录“调用宿主 sampling 回调”，不要记录“检索了互联网研究”。

关键阻断点：服务端在 elicitation 抛异常时会继续模拟预订。这是教学回退逻辑，**不满足真实交易失败即拒绝的要求**。必须先把审批失败改成停止并补测试，才可能接入真实写工具；本课程不进行这类接入。

### 检验恢复而不泄露令牌

保持服务器运行，在第三个终端、相同子目录执行：

```powershell
..\..\..\.venv\Scripts\python.exe -m client.resumable_client --url http://127.0.0.1:8006/mcp
```

`long_running_agent` 有 50 步，每步约 2 秒。收到若干日志后中断**该客户端**，不要停止服务器；再次运行相同命令。预期尝试恢复且最终完成，并清除 `.mcp_resumption_token.json`。日志可能包含恢复标识或片段，不截图、不上传。

为什么使用最小恢复客户端？交互客户端仅在 `last_args` 为真时走自动恢复，而无参 `long_running_agent` 的参数是空字典；令牌管理器也仅在参数为真时保存 `last_args`。因此交互客户端的无参自动恢复存在源码限制，不能照 README 笼统承诺任何工具都可恢复。

默认事件存储不会跨服务器重启保留。可静态对照[事件存储](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/mcp-agents/server/event_store.py)的两个类；不要为了观察效果擅自删除其他实验的 SQLite 文件。

## 可选路线二：追踪 GitHub 与 Chainlit 集成断点

阅读[扩展应用](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/github-mcp/app.py)和[历史运行说明](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/11-agentic-protocols/code_samples/github-mcp/README.md)，本次只读，不执行 `chainlit run`，原因如下：

- 需要额外的 Chainlit、requests、GitHub MCP 服务、GitHub 最小权限凭据、Foundry 模型以及 Azure AI Search。
- `app.py` 顶层会创建/复用固定索引 `event-descriptions`，删除同 ID 文档并重新上传活动文本；只要导入就可能写云资源。共享索引可能被覆盖。
- `on_mcp` 调用 `list_tools()` 后把描述放入 UI 会话；`call_tool` 能找到 MCP 会话，但创建 `GithubAgent` 时没有把这些工具接入智能体工具集合。连接图标出现不等于模型能调用 GitHub 工具。
- `search_events` 会查询 Search 并向 Devpost 发起请求。历史事件文件不是当前活动日历；结果的时间有效性要另查。
- `MCP_SETUP.md` 的端口、令牌变量和旧 npm 服务说明与其他文档并不一致，不能当成已验证的部署步骤。

离线作业：画出 `on_mcp → mcp_tools → call_tool` 与 `on_chat_start → github_agent → on_message` 两条路径，圈出没有连接的工具适配点。说明应先增加受控工具封装与权限校验，再在独立 Search 索引中联调。不要为此申请宽泛 PAT 或生产管理员权限。

## NLWeb 设计验证

本提交无 NLWeb 可执行文件。用三个合成酒店条目设计最小目录：`id`、城市、家庭设施、泳池、更新时间和来源。为“有泳池的东京酒店”写出预期命中 ID，再为“目录未收录的素食餐厅”写出空结果。

交付一份 `ask` 的输入/输出示例，要求输出带来源 ID，并标注房态未实时验证。说明摄取、嵌入、向量检索与 JSON 回答的责任分界；这是一项离线契约验证，不算 NLWeb 联调完成。

## 结果判定与排障

| 现象 | 排查顺序与恢复 |
| --- | --- |
| Foundry 401/403/404 | 核对凭据链、项目数据权限、项目端点与部署名；不打印秘密、不扩大为订阅管理员 |
| 工作流有运行但界面空白 | 查实际事件类型及过滤条件；不要一连重复运行付费调用 |
| MCP 服务连接失败 | 查端口是否被占用、工作目录、服务进程和 SDK 版本；不要关闭认证或系统防火墙 |
| 客户端显示“likely succeeded” | 此提示来自异常回退，不是成功证据；没有有效 `CallToolResult` 就记失败/未知 |
| 恢复失败 | 确认原服务未重启、使用同一工作目录和最小恢复客户端；旧令牌清除后只能开始新任务 |
| 输出说工具/远端工作完成但无证据 | 检查工具注册与执行日志；把模拟和实装拆开记录 |

## 演练记录与清理

记录 OS、Python、核心框架/MCP 版本、模型部署、执行的单元格或命令、预期判据与实际结果。当前交付状态为**待演练**：仅审阅了本地源码，未执行模型调用、MCP 网络实验、GitHub 联调或正式平台校验。

清理前提示：删除恢复令牌会丢失客户端的恢复线索；仅在结束本人的测试后进行。先在客户端输入 `quit`，再在自己的服务终端按 Ctrl+C。仍处于 `mcp-agents` 目录时，可使用两个客户端的专用清理入口：

```powershell
..\..\..\.venv\Scripts\python.exe -m client.client --clean-tokens
..\..\..\.venv\Scripts\python.exe -m client.resumable_client --clear-tokens
```

这些命令只清理各自本地令牌文件，不取消已经提交的远端业务。关闭 notebook 内核，清除有敏感内容的输出；保留去敏作业。若实际创建过 Foundry 智能体或会话，由资源所有者按实验清单清理，不删除共享项目、模型或 Search 索引。
