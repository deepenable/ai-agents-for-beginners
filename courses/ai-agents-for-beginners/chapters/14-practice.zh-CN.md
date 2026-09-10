# 实践六类工作流与受控人工恢复

## 目标、环境与运行约束

本章按顺序、并发、条件、会员中间件、人机协同、交接六条路线练习。最终应能从结构化输出、路由事件和暂停请求判断行为，并识别源码中的模拟、旧 API 与未实现功能。

先完成[环境准备](00-setup.zh-CN.md)及[编排概念](14-concepts.zh-CN.md)。使用 Windows、PowerShell 7、Python 3.12+，固定 `agent-framework-core==1.10.0`。源码版本为 `25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595`；以下单元格号从 1 开始，包括 Markdown。

### 调用、权限和删除风险先行

- 六个 notebook 使用 `FoundryChatClient`、`AzureCliCredential`，需要 Foundry 项目、模型部署、工具调用/结构化输出支持和项目范围权限。先完成 `az login` 与身份核对，不申请整个订阅管理员。
- 顺序至少涉及两个智能体，普通并发涉及三个；性能对照、反例与交接补问会继续增加调用。每条路线只运行一个基线再做必要反例，未经预算批准不要全部运行。
- 酒店库存、会员权益、预订和退款均为模拟。`book_now` 与“Refund Processed”只是生成的文字，不是业务交易回执。不得连接实际下单/退款工具。
- 多个 notebook 含直接拼接模型文本的 HTML 显示代码。只在本机使用合成输入，不把其渲染方式用作生产网页安全方案；作业优先用纯文本字段和去敏事件计数。
- 托管脚本会启动本地服务并调用付费模型；部署还会创建云资源。本章不部署，只提供有边界的可选本机路线。

## 步骤一：建立副本与导入门槛

在源码仓库根执行。已有 `lab-work\14` 时先检查同名文件：

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
New-Item -ItemType Directory -Force .\lab-work\14 | Out-Null
Copy-Item .\14-microsoft-agent-framework\code-samples\14-*.ipynb .\lab-work\14
.\.venv\Scripts\python.exe -c "from agent_framework import WorkflowBuilder, Message, AgentExecutor, FunctionInvocationContext; from agent_framework.foundry import FoundryChatClient; print('base imports OK')"
```

预期核心版本为 `1.10.0`，SHA 与固定值一致，复制得到六个 notebook。最后的 import 只验证本机依赖，不验证云资源。

在编辑器逐个打开副本，使用 `.venv` 内核。切换路线时重启内核并执行该 notebook 自己的定义，防止 `workflow`、`BookingCheckResult` 或会员全局变量串用。不要根据旧 README 改回 `ChatMessage`、`get_new_thread()` 等 API。

交接例外：`HandoffBuilder` 来自额外 orchestrations 集成；根依赖未显式列出它。先测试导入：

```powershell
.\.venv\Scripts\python.exe -c "from agent_framework.orchestrations import HandoffBuilder, HandoffAgentUserRequest; print('handoff imports OK')"
```

若缺包，须选择与核心 1.10.0 兼容的集成版本；可在自己的环境尝试约束安装并检查：

```powershell
.\.venv\Scripts\python.exe -m pip install "agent-framework-core==1.10.0" "agent-framework-orchestrations~=1.10.0"
.\.venv\Scripts\python.exe -m pip check
```

这是兼容性待演练步骤，不保证包源一定有满足约束的版本。若解析失败，停止交接运行，记录冲突并完成其离线事件追踪；不能升级全套框架绕过课程基线。

## 路线一：顺序推荐与审核

来源：[14-sequential.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/14-sequential.ipynb)。

### 配置与补齐输出模式

按单元格 2、4、6 执行导入、Pydantic 模型、Foundry 提供商。单元格 8 创建 `front_desk_agent` 与 `concierge_agent`。源码仅在提示中写模式名称，没有传字段模式；在副本的两个 `as_agent()` 调用中分别补充：

```python
default_options={"response_format": AttractionRecommendation}
```

```python
default_options={"response_format": AttractionReview}
```

`AttractionRecommendation` 包含城市、景点、类别、建议时长等；`AttractionReview` 包含同一景点评分、优缺点和替代建议。两者不应误用同一个模式。

### 建图、运行与判据

单元格 10 的 `WorkflowBuilder` 以 `front_desk_agent` 为入口，用一条直接边连接 `concierge_agent`，并把两者都声明为输出。单元格 11 定义并调用 `display_attraction_recommendation("Stockholm")`，因此执行整格就会收费。

预期前台提出一个景点，礼宾审核同一个景点。彩色标题不是验收证据；可以在该函数的 `outputs = events.get_outputs()` 后加入：

```python
assert len(outputs) == 2
recommendation = AttractionRecommendation.model_validate_json(outputs[0].text)
review = AttractionReview.model_validate_json(outputs[1].text)
print({
    "recommendation_city": recommendation.city,
    "review_city": review.city,
    "same_attraction": recommendation.attraction_name == review.attraction_name,
})
```

还需人工核对评分是否在提示要求范围、事实是否可追溯。模型评分是生成意见，不是实际游客统计。单元格 13 的 `analyze_sequential_flow("Barcelona")` 会再次调用，不是免费重放；预算不足时静态阅读即可。

## 路线二：三个专家并发输出

来源：[14-concurrent.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/14-concurrent.ipynb)。

执行单元格 2、5、7。单元格 9 的三个智能体同样只提及模式名，在副本补充一一对应的 `default_options`：

| 智能体 | 响应模式 |
| --- | --- |
| `attractions_agent` | `AttractionsRecommendation` |
| `dining_agent` | `DiningRecommendation` |
| `history_agent` | `HistoryRecommendation` |

单元格 11 的 `InputDispatcher.forward()` 调用 `ctx.send_message(text)`，`add_fan_out_edges(dispatcher, agents)` 把输入分发到三个智能体，`output_executors=agents` 暴露三个输出。此图不是“景点结果再送给餐饮”；三者面对同一个原始目的地。

执行单元格 13 的 Tokyo 测试前，在 `outputs = events.get_outputs()` 后增加 `assert len(outputs) == 3`，避免原显示函数在缺结果时默默 `continue`。逐个用对应 Pydantic 模型解析，并人工核对输出归属；若顺序/类型与预期不符，先检查实际返回结构，不把错误模式套在另一个专家结果上。

预期三个目的地一致，分别覆盖景点活动、餐饮礼仪、历史文化。三者间若建议冲突，应列为待整合问题；当前代码只有客户端显示，没有 fan-in 审核节点。

单元格 15 的 Paris 与单元格 17 的性能对照均为额外调用。需要性能实验时记录 `measure_concurrent_performance` 和 `measure_sequential_performance` 的时间与输出数量，但不能承诺并发一定更快：限流、服务排队会影响结果，而且顺序图的下游输入包含上游输出，不是完全相同负载。源函数只测一次，不能据此给出稳定性能提升百分比。

## 路线三：按库存做条件分支

来源：[14-conditional-workflow.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/14-conditional-workflow.ipynb)。

依次执行单元格 1、3、5、7、9，创建类型、`hotel_booking`、两个条件函数和输出执行器。工具的可用城市为 Stockholm、Seattle、Tokyo、London、Amsterdam（转为小写后匹配）；Paris 不可用。

继续执行 11、13、15，创建提供商、三智能体与图。当前 notebook 已用 `default_options={"response_format": ...}`，无需套用上一条路线的补丁。

真实控制流为：

```text
availability_agent → no_availability_condition → alternative_agent → display_result
availability_agent → has_availability_condition → booking_agent → display_result
```

运行单元格 17（Paris）后，要求 `outputs_paris` 非空且通过 `AlternativeResult.model_validate_json`；运行 19（Stockholm）后，要求 `BookingConfirmation` 可解析、目的地为 Stockholm、`action` 为 `book_now`。这些只是建议，没有实际预订。

注意两个源码限制：

1. `has_availability_condition` 遇到非 `AgentExecutorResponse` 默认返回 `True`，属于宽松回退。用于真实写动作前应改为显式错误或失败即拒绝。
2. 两个条件遇到 JSON 解析错误都可能返回 `False`，导致没有分支输出。不能把空输出视作成功；在测试单元格加 `assert outputs_paris` / `assert outputs_stockholm`。

替代城市由模型生成，未再次调用 `hotel_booking` 验证。合格报告须标注这一事实，不把替代推荐当成库存保证。

## 路线四：会员中间件改变工具结果

来源：[14-middleware.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/14-middleware.ipynb)。

这条路线只在自己的单用户内核运行。将会员示例数据限定为 `priority_user` 与 `regular_user` 等合成标识，不输入真实邮箱。顺序执行定义至单元格 20。

单元格 10 的 `priority_check_middleware`：

1. 取得 `context.function.name`；
2. `await next(context)` 执行原始工具；
3. 解析 `context.result`；
4. 若会员且无房，改为 `has_availability=True`、`priority_override=True`；
5. 让后续模型和条件边消费修改后的结果。

它通过单元格 18 的 `middleware=[priority_check_middleware]` 注入 availability 智能体。`BookingCheckResult.priority_override` 是必需字段；普通用户和本来有房的分支也应明确为 `False`。为减少让模型猜该字段，可在**副本**工具的 `result` 字典中增加 `"priority_override": False`，会员覆盖时再改为 `True`。

依次运行三个测试并核对：

| 输入 | 工具原始房态 | 中间件后 | 预期路由 |
| --- | --- | --- | --- |
| `regular_user` + Paris（单元格 22） | 无房 | 无覆盖 | 替代城市 |
| `priority_user` + Paris（24） | 无房 | 模拟有房、覆盖标记真 | 预订建议 |
| `priority_user` + Stockholm（26） | 有房 | 不需覆盖 | 预订建议 |

在中间件内只记录函数名、布尔房态与是否覆盖，不记录真实身份。必须保留“原结果”和“后结果”的区别；仅看到最终 `book_now` 无法证明中间件执行。

此源码使用全局 `current_user_id`，不支持多用户安全并发。扩展题是把它替换成认证请求上下文，并用真实会员库存查询代替布尔改写。不要在课堂把库存改写逻辑接到真实系统。

## 路线五：显式暂停与恢复人工输入

来源：[14-human-loop.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/14-human-loop.ipynb)。

### 阅读当前执行路径

依次执行定义至单元格 19。重点读单元格 11 的 `DecisionManager`：

- `on_confirmation` 验证 `ConfirmationQuestion`，调用 `ctx.request_info(...)`，以 `HumanFeedbackRequest` 携带目的地和提示；
- `on_human_feedback` 用 `@response_handler` 接收字符串，`yes` 发送替代请求，`no` 或其他内容发送取消请求。

单元格 13 的 `prepare_human_request` 存在但不在当前 `.add_edge()` 图中。旧文字里的 `RequestInfoExecutor` 也没有被创建并接入；不要为了匹配旧界面说明再添加一套不兼容节点。

### 跑完正向，再跑拒绝与异常输入

单元格 21 的默认 `SCRIPTED_ANSWER="yes"` 不是人工审批。先按默认模拟跑一次，预期：

1. Paris 无房；
2. 出现 `request_info`，携带 `event.request_id` 和请求数据；
3. 外层用该请求 ID 构造 `responses`；
4. 同一个工作流 `run(stream=True, responses=responses)` 恢复；
5. 最终输出为替代城市 JSON。

简短的恢复调用形式是：

```python
stream = workflow.run(stream=True, responses={pending_request_id: "no"})
```

这里 `pending_request_id` 必须来自这次尚未回答的事件，不能使用示例字符串或另一个工作流的 ID。上面的片段说明接口，不应在没有暂停请求时盲跑。

接着在副本分别把 `SCRIPTED_ANSWER` 改成 `"no"`、`"maybe"`。每个新测试先重新执行智能体/执行器创建单元格 17 和建图单元格 19，再运行 21，避免重复使用已消费的请求。预期两者都走取消路径，JSON 的 `status` 应为 `cancelled`。

增加断言，不接受原显示代码“不是替代对象就当作取消”的宽松判断：

```python
assert workflow_output is not None
result_data = json.loads(workflow_output)
if SCRIPTED_ANSWER == "yes":
    AlternativeResult.model_validate(result_data)
else:
    assert result_data.get("status") == "cancelled"
```

按预算另测 Stockholm（单元格 23），预期无人工请求，直接给预订建议。它不扣款，所以没有购买审批；如果以后新增真实预订工具，无论有无房都应增加动作级审批。

实际应用应由 UI/命令行收集身份明确的答复，设置超时和恢复次数上限。样例外层 `while True` 未提供持久检查点或生产级等待超时，不能声称它已支持跨进程审批恢复。不要只把 `SCRIPTED_ANSWER` 从 yes 改成固定 no 就称为实现了人工控制。

## 路线六：客服向专家交接

来源：[14-handoff.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/14-handoff.ipynb)。

通过前述 orchestrations 导入门槛后，依次执行 3、5、7、9、11、13。四个智能体为客服入口、订票、争议退款、行程核对。源码使用 `require_per_service_call_history_persistence=True`，并由 `HandoffBuilder` 注册交接目标。

`build_workflow()` 每次创建新图，因为相同 workflow 的多次 `run()` 保留状态。终止条件统计用户消息数大于 3，不代表业务问题已解决；测试中最多两条脚本补充答复，可能仍留有待输入请求。

辅助函数职责：

| 函数 | 做什么 |
| --- | --- |
| `drain_events` | 消费并保存本次流式事件 |
| `_output_messages` | 从不同 output 数据形状提取 `Message` |
| `handle_workflow_events` | 打印 `handoff_sent` / 状态，并返回待答复请求 |
| `collect_output_messages` | 汇集输出消息，按作者核对专家 |

执行测试前，把脚本姓名、联系方式与票号改为明确合成标识，不填真实客户数据：

- `test_booking_handoff`（单元格 15）：客服应交给 `booking_agent`。
- `test_dispute_handoff`（17）：取消/退款应交给 `disputes_agent`。
- `test_trip_check_handoff`（19）：行程确认应交给 `trip_check_agent`。

每条在有预算时运行一次。要求出现对应 `handoff_sent` 事件、正确专家的输出，并能解析相应 Pydantic 类型。只依据输出作者推测路由不如真实交接事件可靠。

补充输入使用：

```python
responses = {
    req.request_id: HandoffAgentUserRequest.create_response(user_response)
    for req in pending_requests
}
```

只对当前待处理请求答复；若还存在 `pending_requests`，记录“等待输入”，不要把脚本答复用完当作业务完成。不要无限补问直到打印成功。

单元格 21 的 `analyze_handoff_patterns` 又运行四个请求，属于额外费用。它可用于观察动态分诊，但当前只有客服到专家的交接边，没有完整专家之间互转或群聊。

这里的专家指令要求“总是确认订票”“总是同意退款”，没有真实后端工具。因此所有确认与退款金额均是合成输出，不能用于财务或售后业务。

## 可选 Python 变体一：独立酒店脚本的迁移练习

来源：[hotel_booking_workflow_sample.py](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/hotel_booking_workflow_sample.py)。

此脚本与更新后的 notebook 不同：仍使用 `ai_function`、`ChatMessage`、`Role`、`create_agent`、旧构建器风格，并按 MiniMax → Azure OpenAI → OpenAI 优先选择后端。仅仅环境中存在非空 MiniMax 变量就会选中该服务，产生独立认证和费用要求。

它还给 `OpenAIChatClient` 传 `azure_endpoint`、`credential` 并注释为 Responses，不能据注释认定在 1.10.0 中可用。因此此文件列为**迁移/静态阅读变体**，不推荐直接执行。

有意义的迁移作业是对照条件 notebook，在自己的副本中：

1. 将工具改为 `@tool`，消息改为 `Message(role="user", contents=[...])`；
2. 统一为已批准的 `FoundryChatClient` 与两个 Foundry 变量；
3. 使用 `as_agent`、`default_options`、`WorkflowBuilder(start_executor=..., output_executors=...)`；
4. 保留 `asyncio.run(main())` 的脚本入口与两种城市测试；
5. 增加空输出和未知类型失败断言，移除“异常默认有房”的路径。

这样仍是学习者的新迁移副本，不是原脚本已验证通过。未做迁移时，使用前面的条件 notebook 主线完成可执行实验即可。

## 可选 Python 变体二：本机托管 LangGraph 响应入口

来源：[14-langchain-hosted-agent.py](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/14-microsoft-agent-framework/code-samples/14-langchain-hosted-agent.py)。

只有资源和费用获批后才执行；不需要为本机验证申请云托管部署角色。此路线额外依赖 `langchain-azure-ai[hosting]>=1.2.4`、`langchain-openai`、`azure-ai-projects`、`azure-identity`。版本范围不是完整锁文件，应隔离于主线环境并记录解析版本。

源码根工作目录：

```powershell
py -3.12 -m venv .venv-hosting
.\.venv-hosting\Scripts\python.exe -m pip install "langchain-azure-ai[hosting]>=1.2.4" langchain-openai azure-ai-projects azure-identity
.\.venv-hosting\Scripts\python.exe -m pip check
```

先通过本地安全渠道取得项目端点和部署名。此脚本没有调用 `load_dotenv()`，所以不能只写根 `.env`；应在即将启动服务的同一个 PowerShell 终端设置进程环境变量。将以下两个占位符替换为自己的已批准值，勿把真实值提交到作业：

```powershell
$env:FOUNDRY_PROJECT_ENDPOINT = 'https://<project-resource>.services.ai.azure.com/api/projects/<project-name>'
$env:FOUNDRY_MODEL_NAME = '<deployed-model-name>'
$env:PORT = '8088'
```

这些变量不是 `AZURE_AI_PROJECT_ENDPOINT` 的自动别名。模型需支持选用的 API；`build_chat_model()` 使用 `DefaultAzureCredential`，应核对实际身份。

检查端口 8088 没被自己的其他服务占用，并确认宿主监听范围和主机防火墙不会对外暴露未授权服务，再在源码根运行：

```powershell
.\.venv-hosting\Scripts\python.exe .\14-microsoft-agent-framework\code-samples\14-langchain-hosted-agent.py
```

保留该终端；不要把它部署到公网。在第二个本机终端发送一次合成请求，**此请求触发付费模型调用**：

```powershell
$body = @{ input = 'Give one tip for testing a synthetic travel agent.'; stream = $false } | ConvertTo-Json
$result = Invoke-RestMethod -Method Post -Uri 'http://localhost:8088/responses' -ContentType 'application/json' -Body $body
$result | Select-Object id, status
```

预期 HTTP 成功，返回可辨识的响应 ID/状态与非空回答内容；不要只凭服务已监听就判模型成功。`ResponsesHostServer` 提供外部 Responses 入口，而内部 `ChatOpenAI` 的实际调用模式仍须按所装版本检查，若报 API 不支持就停止，不盲目切换模型/部署。

脚本 `tools=[]`，未配置 durable checkpointer 或人工中断，也未实现 Invocations 入口。即使基础响应成功，也不能声称会话持久化、人工恢复、自动扩缩和云部署均已验证。本课程不运行脚本注释中的 `azd provision` / `azd deploy`。

## 通用排障与验收记录

| 现象 | 排查与恢复 |
| --- | --- |
| `agent_framework.orchestrations` 导入失败 | 根清单缺少显式集成；核对兼容版本，失败则记录阻断，不升级核心 |
| JSON 解析失败 | 核对对应 `response_format`、实际输出类型、必需字段；不把 Markdown 围栏字符串硬当合法 JSON |
| 没输出却显示完成标题 | 增加非空和模式断言；查条件解析错误或过滤掉的事件 |
| 人工恢复找不到请求 | 保持原暂停中的 workflow，用当前未消费的请求 ID；新场景重建图 |
| 会员测试串结果 | 确认 `set_user`、内核与新图，禁止多用户并发共享全局变量 |
| 并发慢或 429 | 降低并发与重复测试，遵循服务退避提示，检查配额与调用预算 |
| 模型 401/403/404 | 检查实际凭据、项目端点、部署名和权限；不把 Azure OpenAI 端点与 Foundry 项目端点混用 |
| 旧酒店脚本报参数/导入错误 | 使用 notebook 主线，按迁移作业改自己的副本；不把旧注释作为 SDK 契约 |

每条实际运行路线填写：日期、OS、Python、核心与集成版本、模型/API、输入场景、工具/事件证据、输出校验、调用次数、未完成项。六条路线分别记通过、失败或未执行；不能用一次顺序工作流的成功代表整个模块。

## 当前状态与清理

当前为**待演练**：本次只进行了固定版本源码本地审阅，未执行六类云工作流、付费模型调用、本地托管请求或部署，也未运行平台正式验证器。文中的输出均为预期判据。

在自己启动的服务终端按 Ctrl+C，确认进程已停止；关闭 notebook 内核。不要按进程名批量杀死 Python 或删除其他人的端口占用。清除含真实资料的输出，保留去敏结果表。

如不再需要，先在源码根检查 `lab-work\14` 与自己的两个可选虚拟环境，用 `Remove-Item -WhatIf` 预览明确路径，再决定删除；不要删除原始样例和共享 `.venv`。Foundry 运行可能留下实验智能体、会话或响应历史，交由有权限的资源所有者按本次 ID 清单清理；不删除共享项目、模型或整个资源组。
