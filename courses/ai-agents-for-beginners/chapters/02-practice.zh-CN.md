# 用工具和会话实现两轮目的地查询

## 学习目标与准备

本实验使用四层架构实现多轮库存查询，验证同一个 `AgentSession` 如何保留上下文，并检查未知城市与大小写造成的边界问题。选做部分对比直接 Azure OpenAI Python 路径和 C# 会话实现，不替代主线。

先完成[环境准备](00-setup.zh-CN.md)及[框架概念](02-concepts.zh-CN.md)。在源码仓库根使用 PowerShell 7、Python 3.12+ 和 `.venv` 内核；核心包须为 `1.10.0`。主线使用 Foundry 项目端点、已部署模型和 `AzureCliCredential`，要求项目数据访问与推理权限。

**费用与权限警告：** 每轮模型调用可能包含多次工具往返。不要用大量追问探索完整城市列表；先限定测试用例。所有库存都是静态演示数据，绝不能用于真实订单。读工具可自动执行，未来换成预订或写入工具时必须重新设计审批、授权及幂等性。

## 步骤一：定位主线并跳过旧安装命令

本地文件为 `02-explore-agentic-frameworks\code_samples\02-python-agent-framework.ipynb`，对应[固定版本源码](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/02-explore-agentic-frameworks/code_samples/02-python-agent-framework.ipynb)。单元格编号包含 Markdown。

```powershell
Test-Path .\02-explore-agentic-frameworks\code_samples\02-python-agent-framework.ipynb
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
```

预期为 `True` 和 `1.10.0`。打开 notebook 后跳过第 3 格中的未锁定安装和升级命令；用环境准备章的根依赖，不执行 `pip install ... -U`。

运行第 4 格导入，再运行 `Understanding the Agent Framework Architecture` 下第 6 格客户端初始化。该格检查 `AZURE_AI_PROJECT_ENDPOINT` 和 `AZURE_AI_MODEL_DEPLOYMENT_NAME`，然后构造 `FoundryChatClient`。配置检查不应打印真实端点或凭据；成功初始化也不代表服务授权已经验证。

## 步骤二：理解工具的完整数据边界

运行 `Adding Tools with the @tool Decorator` 下第 8 格。实际数据为：

```python
available = {
    "Barcelona": True,
    "Tokyo": True,
    "Cape Town": False,
    "Vancouver": True,
    "Dubai": False,
}
is_available = available.get(destination, False)
```

函数 `check_destination_availability` 使用精确字典键查找，`Annotated[str, ...]` 提供参数说明。它只检查一个目的地，没有向模型枚举城市的接口。未知键默认 `False`，因此工具返回 `not available` 时，可能是明确不可用，也可能是根本没有该城市。

先做不调用云端的纸面预判：

| 参数 | 从源代码推导的结果 |
| --- | --- |
| `Barcelona` | available |
| `Cape Town` | not available |
| `barcelona` | not available，键的大小写不匹配 |
| `Atlantis` | not available，未知键落到默认值 |

为验证模型实际用了哪些参数，可在练习副本中、`is_available` 之后添加：

```python
print(f"[availability] destination={destination!r}; available={is_available}")
```

只用于固定城市名测试；将来接入个人数据时不要直接记录所有参数。重新执行该工具定义格，使注册的函数含观察标记。

## 步骤三：创建智能体并执行两轮

运行 `Creating an Agent with Tools` 下第 10 格。实际 API 是：

```python
agent = provider.as_agent(
    name="TravelAvailabilityAgent",
    instructions=(
        "You are a travel booking agent. Help users check destination availability "
        "and make recommendations. Always check availability before recommending a destination."
    ),
    tools=[check_destination_availability],
)
```

忽略相邻源 Markdown 中 `provider.create_agent()` 的旧写法，不在当前代码中替换已存在的 `as_agent`。

定位 `Multi-Turn Conversations with Sessions`，先运行第 12 格，再运行第 13 格：

```python
session = agent.create_session()
response = await agent.run(
    "Which destinations do you have available?", session=session
)
print(f"Agent: {response}")
response = await agent.run(
    "I'd like to go somewhere warm. What's available?", session=session
)
print(f"Agent: {response}")
```

第一轮问题要求枚举，但当前工具只能按名检查。模型可能试探多个城市或要求澄清，不能保证列出字典中全部五项。**不要把“没有列出所有可用城市”与“会话失效”混为一谈。** 更不可认为模型未提及的城市一定售罄。

第二轮应利用同一个会话中的上下文，结合温暖偏好重新建议，并在推荐前检查候选。库存工具没有气候字段，所谓温暖是模型知识或假设，不是库存工具验证结果。

## 步骤四：用具体城市验证会话

下面是本手册的补充测试，在原示例运行后新增格执行。会产生两次额外云端请求，先确认预算；使用新会话避免被原始开放问题干扰。

```python
case_session = agent.create_session()
first = await agent.run(
    "Please check Barcelona and Cape Town. Remember that I prefer Barcelona.",
    session=case_session,
)
print(first)
second = await agent.run(
    "Is my preferred destination available? Check it again.",
    session=case_session,
)
print(second)
```

验收时看观察标记而不仅是答案文案：第一轮应检查 Barcelona 与 Cape Town；第二轮应理解“preferred destination”为 Barcelona，并重新检查它。应保留 Cape Town 不可用的事实，不应声称已订票。

如果需要新会话对照，另建 `agent.create_session()` 后只发送第二个问题。它没有本测试的偏好历史，应澄清或承认不知道偏好。该对照另计一次模型调用，不必为了过关无限重试。

### 改进思考

生产工具应将“未知”和“不可用”分开，并明确参数规范化规则。可以在个人副本设计 `status` 为 `available / unavailable / unknown` 的结构化结果，但不要悄悄修改源字典后把结果当成原版本表现。初次完成只要求识别并记录缺陷。

## 可选：直接 Azure OpenAI 的 Python 变体

[变体 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/02-explore-agentic-frameworks/code_samples/02-python-agent-framework-azure-openai.ipynb)的本地文件是 `02-explore-agentic-frameworks\code_samples\02-python-agent-framework-azure-openai.ipynb`。它读取 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_DEPLOYMENT`，不是项目端点变量；以 `OpenAIChatClient(..., azure_endpoint=endpoint, credential=AzureCliCredential())` 走源版本所述 Azure OpenAI v1 Responses 路线。

执行前额外确认该资源的推理权限、Responses 支持和预算。跳过第 2 格安装；依次执行 `Import the Needed Python Packages`、`Defining a Tool`、配置格、`Creating the Agent` 和 `Running the Agent`。不要因端点错误把 Foundry 项目 URL 填入 `azure_endpoint`。

实际工具 `get_random_destination` 用 `_DESTINATIONS` 和 `_last_destination` 排除紧邻上次的城市：

```python
available = _DESTINATIONS.copy()
if _last_destination and len(available) > 1:
    available.remove(_last_destination)
destination = random.choice(available)
_last_destination = destination
```

第 11 格 `main()` 为两条 `user_inputs` 复用一个会话，流式累积回答后用 notebook 的 HTML 显示功能展示。这里的 HTML 是源程序的界面输出，不是本手册的嵌入组件，平台不会执行它。

判据是两轮响应正常结束，第二次随机工具调用不紧邻重复。全局变量在内核重启后清空，也可能被不同会话共同使用；不能将它理解为按用户隔离的永久偏好。

## 可选 .NET 与门户路线

[02 C# 源文件](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/02-explore-agentic-frameworks/code_samples/02-dotnet-agent-framework.cs)使用 `GetRandomDestination`、`AIFunctionFactory.Create`、`CreateSessionAsync` 和两次 `RunStreamingAsync`。它没有 Python 变体的 `_last_destination` 排重逻辑，不能要求两轮随机工具必然不同。

准备 .NET 10+、Azure OpenAI 两个变量和本人 CLI 身份后，预算允许才在源码根运行：

```powershell
dotnet run .\02-explore-agentic-frameworks\code_samples\02-dotnet-agent-framework.cs
```

该文件 NuGet 含浮动版本，演练必须记录实际解析值。其 `GetChatClient` 是 Chat 路径，不应按源说明中的 Responses 标签推断实现。检查第二轮是否利用同一 `AgentSession` 理解“that destination”。

[门户 FlightAgent 补充路线](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/02-explore-agentic-frameworks/azure-ai-foundry-agent-creation.md)可作为界面观察选读：对照名称、模型部署、Instructions、Knowledge 和 Actions 字段与本章四层架构。它不接实时数据，创建多个智能体也不自动形成协作系统。本主线不要求按旧 hub 菜单部署任何资源。若选做创建，必须先确认资源费用和创建权限；不得执行原指南的整个资源组删除来清理共享项目。

## 故障排查

| 现象 | 排查与恢复 |
| --- | --- |
| 第 6 格缺少配置 | 核对变量名称及工作目录，修改后重启内核，不展示 `.env` |
| 401/403 | 核对实际 CLI 身份、目标端点的数据权限；直接 OpenAI 与 Foundry 权限不是同一项 |
| 404/不支持模型 | 检查部署名与端点种类，再检查服务和模型支持；不要换 API 字段盲试 |
| `create_agent` 不存在 | 当前实际代码使用 `as_agent`；不要照抄过时解释格 |
| 第二轮忘记偏好 | 是否意外重建 `session`、重启内核或漏传 `session=session` |
| Barcelona 被说成不可用 | 检查实际参数是否为小写或含国家后缀，而非先归因于模型能力 |
| 列表看似不完整 | 工具只做逐项检查，不提供枚举；换具体测试用例，不让模型无界猜测 |
| 429/循环检查很多城市 | 停止调用，限定候选，确认配额与退避要求 |

## 验收、清理与演练状态

主线验收记录应包含：四层与代码对应关系、同一会话两轮对话、至少一个已知可用与不可用城市的工具证据、未知键和大小写缺陷说明。选做路线单独记，不把未执行写成失败或通过。

停止内核，删除或清理个人副本中的测试输出及观察标记；重启会清除 Python 全局随机状态，但不是云端数据删除。Foundry 中按本次名称 `TravelAvailabilityAgent`、运行时间和对象标识核对实验智能体与会话；只有确认归属后才删除。删除前检查其他人是否依赖该对象，保留后续实验需要的共享模型与项目，不删除整个资源组。直接 Azure OpenAI 路线也须按资源保留政策处理服务端记录，不能假定退出程序即抹除。

**教学演练状态：待演练。** 未进行模型调用、门户创建或 .NET 运行；上述均为操作说明及预期验收标准。
