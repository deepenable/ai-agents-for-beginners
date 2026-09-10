# 实作结构化旅行计划与工具执行

## 学习目标与准备

本章用两个阶段完成旅行任务：`TravelPlanner` 生成 `TravelPlan`，`Concierge` 读取计划并调用模拟工具。验收重点是字段、依赖和调用证据，不是获得真实机票。先完成[环境准备](00-setup.zh-CN.md)与[规划概念](07-concepts.zh-CN.md)。

环境：Windows PowerShell 7、Python 3.12+，核心依赖固定 `agent-framework-core==1.10.0`。主线需要 Microsoft Foundry 开发项目、部署名和允许调用模型及使用实验智能体的项目数据权限。

源码入口：[07-python-agent-framework.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/07-planning-design/code_samples/07-python-agent-framework.ipynb)。单元格索引从 `cells[0]` 起，包含 Markdown。

## 步骤一：打开正确内核，跳过漂移安装

在源码根运行：

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
Test-Path .\07-planning-design\code_samples\07-python-agent-framework.ipynb
```

预期 SHA 与准备章一致、核心包为 `1.10.0`、文件存在。打开 notebook，选用 `.venv`。**跳过索引 2 的 `%pip install agent-framework ...`**，因为课程依赖已由根 `requirements.txt` 安装；重复安装元包可能改变兼容关系。

配置 `AZURE_AI_PROJECT_ENDPOINT` 和 `AZURE_AI_MODEL_DEPLOYMENT_NAME`；索引 3 验证是否缺失，索引 4 建立：

```python
client = FoundryChatClient(
    project_endpoint=endpoint,
    model=deployment_name,
    credential=DefaultAzureCredential()
)
```

不要把直接 Azure OpenAI 资源端点用于此构造函数。`DefaultAzureCredential` 的身份选择按准备章排查，不输出完整凭据链内容。

## 步骤二：先读懂计划模型

运行 `Task Decomposition` 下的索引 6。以下是源码中的任务模型：

```python
class TravelSubTask(BaseModel):
    task_id: int
    description: str
    assigned_agent: str
    priority: str
    dependencies: list[int] = []
```

`TravelPlan` 包含 `destination`、`trip_duration_days`、`subtasks`、`total_estimated_budget_usd`、`notes`。检查模型定义后回答：哪个字段表示先后依赖，哪个只是重要性？如果模型给出不存在的执行者，会自动失败吗？答案是 `dependencies` 表示依赖；`priority` 表示优先级；普通字符串不会自动验证注册表。

无需云调用时，可在新增单元格实例化一份离线计划：

```python
offline_plan = TravelPlan(
    destination="Paris",
    trip_duration_days=7,
    subtasks=[
        TravelSubTask(task_id=1, description="Compare flights", assigned_agent="flight_agent", priority="high"),
        TravelSubTask(task_id=2, description="Compare hotels", assigned_agent="hotel_agent", priority="high", dependencies=[1]),
    ],
    total_estimated_budget_usd=5000,
    notes="Synthetic plan only; no reservations.",
)
assert offline_plan.subtasks[1].dependencies == [1]
```

预期对象能建立；这只验证数据模型，不证明有真实航班或酒店。

## 步骤三：生成一次结构化计划

**费用提示：从此步起 `planning_agent.run` 和后续 `concierge_agent.run` 都会产生模型调用费用，工具调用过程还可能触发多轮模型请求。仅使用批准的开发预算。**

运行 `Creating a Planning Agent with Structured Output` 的索引 8。源码使用：

```python
result = await planning_agent.run(
    "Plan a 7-day trip to Paris for a couple interested in art, cuisine, and history. Budget around $5000.",
    options={"response_format": TravelPlan}
)
```

读取 `result.value`，不照搬 README 中另一套 `AgentEnum` 模型。若没有值或类型不符，立即停止，不进入索引 10。

在学习副本添加业务校验。以下只操作已有对象，不联网：

```python
plan = result.value
assert isinstance(plan, TravelPlan)
assert plan.destination.lower() == "paris"
assert plan.trip_duration_days == 7
assert plan.subtasks
assert 0 < plan.total_estimated_budget_usd <= 5000
ids = {t.task_id for t in plan.subtasks}
assert len(ids) == len(plan.subtasks)
allowed = {"flight_agent", "hotel_agent", "activity_agent"}
assert all(t.assigned_agent in allowed for t in plan.subtasks)
assert all(t.priority in {"high", "medium", "low"} for t in plan.subtasks)
assert all(set(t.dependencies) <= ids and t.task_id not in t.dependencies for t in plan.subtasks)

pending = {t.task_id: set(t.dependencies) for t in plan.subtasks}
done = set()
while pending:
    ready = [task_id for task_id, deps in pending.items() if deps <= done]
    assert ready, "Dependency cycle detected"
    for task_id in ready:
        done.add(task_id)
        del pending[task_id]
```

此处把 5000 当作课堂硬上限，而源请求的 “around” 比较宽松；如果预算断言失败，不是 SDK 故障，应调整用户约束或计划。源码提示还提到 logistics，但没有对应工具；出现其他 `assigned_agent` 时应标注“当前执行能力不支持”，先修订计划，不能擅自放宽 allowlist。

## 步骤四：审查模拟工具再执行

`Executing a Plan with Specialist Tools` 的索引 10 同时定义工具、创建 `Concierge` 并执行请求。**不要在未审查时整格运行：如果学习副本接过真实预订接口，必须先恢复为源码模拟函数。真实预订、取消或付款须先人工批准，不能沿用本格直接执行。**

三个工具及其输入如下：

| 工具 | 参数 | 源码实际行为 |
| --- | --- | --- |
| `book_flight` | `destination`、`departure_date`、`return_date` | 返回航班确认文本 |
| `reserve_hotel` | `city`、`check_in`、`check_out`、`guests` | 返回酒店确认文本 |
| `book_activity` | `activity_name`、`date`、`participants` | 返回活动确认文本 |

它们只使用字符串和 `hash`，没有网络或支付 SDK。日期类型是字符串，没有自动校验结束晚于开始、人数为正或预算足够。原请求没有绝对日期，执行时应人工标出模型生成的日期是演示假设。

确认 `plan` 有效后运行索引 10。`subtask_lines` 把任务与依赖串为文本，`execution_prompt` 交给 `concierge_agent.run`。这不是确定性的任务路由器：代码没有根据 `assigned_agent` 字典派发，也未强制按拓扑顺序执行。

可在副本每个工具函数体入口添加只记录工具名和虚构参数的本地记录列表，用来核对调用顺序；不要记录真实旅客信息。否则只凭最终文字无法证明所有工具都被调用。

验收：输出覆盖计划中的可支持任务；工具调用参数与目的地、人数和日期一致；未完成任务被明确报告；确认号不要求跨次相同。不能把 “Flight booked” 当作航空公司凭证。

## 步骤五：受控重规划

在副本保留原 `plan.model_dump_json()` 作为前一计划，再给 `planning_agent.run` 一个新请求：保持巴黎与两位旅客，但缩短为五天，并说明上一计划尚未进行真实预订。仍使用 `options={"response_format": TravelPlan}`。

这是一项新增练习，原 notebook 没有自动重规划函数。每次最多重新生成一个候选，重新跑业务校验，把天数断言改为 5。比较任务增删、预算、酒店与活动依赖是否同步变化。没有通过校验就停止，不重复执行旧计划，更不能对真实已完成任务重放。

## 可选 .NET：另一种结构化计划

阅读[07-dotnet-agent-framework.cs](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/07-planning-design/code_samples/07-dotnet-agent-framework.cs)及[配套说明](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/07-planning-design/code_samples/07-dotnet-agent-framework.md)。file-based `.cs` 路线需 .NET 10+，不能直接沿用旧说明的“.NET 9 即可”。

它读取 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_DEPLOYMENT`，使用 `AzureCliCredential`、`AzureOpenAIClient.GetChatClient(...).AsAIAgent(...)`，不是 Python 的 Foundry 项目客户端。虽然注释写 Responses，实际调用的是 `GetChatClient`；不能据此声称与 Python Responses 路线相同。

重点比较：

1. `Plan` 的 `assigned_agent`、`task_details` 与 Python 的任务 ID、优先级、依赖字段不同。
2. `TravelPlan` 只有 `main_task` 和 `subtasks`，不直接表示预算或天数。
3. `ChatResponseFormatJson.ForJsonSchema` 与 `AIJsonUtilities.CreateJsonSchema(typeof(TravelPlan))` 定义输出契约。
4. `AGENT_INSTRUCTIONS` 被放在 `ChatClientAgentOptions.Description`，不是明显的 `instructions` 参数。不要认为描述字段一定替代系统指令；运行前需由维护者核对该 NuGet 版本语义。

该文件含 `10.*`、`1.*-*` 等浮动 NuGet 声明，没有本课程核定的完整锁定组合。因此本次可选路线先做代码对照，标记运行待演练；不为演示自动解析最新版依赖。接收方确认兼容版本、固定学习副本依赖并批准预算后，才在源码 `07-planning-design\code_samples` 目录使用 file-based 运行方式：

```powershell
dotnet --version
dotnet run .\07-dotnet-agent-framework.cs
```

运行会联网恢复包并调用模型。验收应是输出能按 `TravelPlan` 反序列化、子任务有名称和描述，而不是实际完成预订。

## 故障、清理与记录

| 现象 | 恢复方法 |
| --- | --- |
| 缺包或 `response_format` 行为不符 | 检查选中内核及核心包版本；回到准备章隔离环境，不运行 notebook 的浮动安装格 |
| `result.value` 为空或无法解析 | 停在规划阶段，核对模型对结构化输出的支持；保留去敏异常，最多受控重试 |
| 未知任务、依赖环、重复 ID | 作为业务验证失败，反馈给规划器；不要直接删除依赖以便执行 |
| Concierge 漏掉任务或顺序错误 | 检查计划文本与工具参数；记录真实调用证据，区分提示约束和程序约束 |
| 401/403/429 | 核对身份和项目数据权限；降低请求量、按退避提示处理，不增加权限或连续重试 |
| .NET 无法识别 `#:package` 或 API | 检查 .NET 10+ 和固定的兼容依赖；没有锁定验证前保持可选分支阻塞 |

清理前核对所有对象都属于本次实验。关闭内核，删除含假设日期、个人信息或模型输出的学习副本输出；保留去敏计划与检查结果。模拟工具没有预订需要取消。Foundry 服务端可能保留实验智能体及会话，应由资源所有者按本次记录的对象逐一清理；不要按名称批量删除同名共享智能体或模型部署。

**教学演练状态：待演练。** 记录 Python/SDK 实际版本、计划校验结果、真实调用证据、未支持的任务与可选 .NET 阻塞。没有云端调用或 .NET 构建验证时必须写“未执行”。
