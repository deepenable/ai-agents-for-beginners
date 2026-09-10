# 创建并验证第一个旅行推荐智能体

## 学习目标

本实验把[智能体概念](01-concepts.zh-CN.md)落实为四项可检查操作：连接 Foundry 项目、注册一个只读 Python 工具、运行一次推荐、观察流式输出。你还要证明“城市列表来自工具”和“景点描述由模型组织”是不同事实，不能仅凭一段漂亮回答判定成功。

## 准备与执行前风险

先完成[环境准备](00-setup.zh-CN.md)。工作目录为固定提交的源码仓库根，目标为 Windows、PowerShell 7、Python 3.12+；使用该仓库 `.venv` 的 notebook 内核。需要已批准的 Foundry 项目、支持工具调用的模型部署、`AZURE_AI_PROJECT_ENDPOINT` 与 `AZURE_AI_MODEL_DEPLOYMENT_NAME`，以及代码所用 `AzureCliCredential` 可访问的身份。

**在运行 `agent.run` 前确认预算和项目范围权限。** 两个示例请求都会调用云端模型，工具调用还可能带来额外模型往返；无真实订票费用不等于无推理费用。只输入虚构旅行偏好，不输入护照、银行卡或个人行程。`approval_mode="never_require"` 只适用于此处返回固定列表的只读工具。

源文件：[01 Python notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/01-intro-to-ai-agents/code_samples/01-python-agent-framework.ipynb)。本地路径为 `01-intro-to-ai-agents\code_samples\01-python-agent-framework.ipynb`。以下单元格编号从文件第一个单元格开始计数，包含 Markdown；用标题和函数名定位更稳妥，不是执行计数 `In[n]`。

## 步骤一：核对源码与内核

在源码根打开 PowerShell 7：

```powershell
git rev-parse HEAD
Test-Path .\01-intro-to-ai-agents\code_samples\01-python-agent-framework.ipynb
.\.venv\Scripts\python.exe -c "import sys; from importlib.metadata import version; print(sys.version.split()[0]); print(version('agent-framework-core'))"
```

应分别得到固定 SHA、`True`、不低于 3.12 的 Python 和 `1.10.0`。这些是预期判据，不是已执行记录。打开 notebook 并选择同一 `.venv` 内核。

**跳过 `Setup` 下第 3 格的 `%pip install agent-framework ...`。** 它未锁定版本；不要运行“全部执行”把它一起执行。依赖以根 `requirements.txt` 为准，不执行升级整个 `agent-framework` 的命令。

运行第 4 格导入、`dotenv.load_dotenv(dotenv.find_dotenv())`、变量检查及 `FoundryChatClient` 初始化。不得打印 `.env` 或令牌。变量检查通过只证明配置非空；实际授权在首次远程调用时才能判定。

## 步骤二：阅读并定义工具

定位 `Creating Your First Agent`，运行第 6 格 `get_destinations`。关键结构如下，完整城市列表保留在源 notebook：

```python
@tool(approval_mode="never_require")
def get_destinations() -> list[str]:
    """Get a list of popular vacation destinations."""
    return [
        "Barcelona", "Paris", "Berlin", "Tokyo", "Sydney",
        "New York City", "Cairo", "Cape Town", "Rio de Janeiro", "Bali",
    ]
```

这是无参数、固定结果的本地工具；模型看到的说明来自 docstring，返回类型来自类型注解。当前函数不会检查可预订性，也不会自动根据季节筛选城市。

在自己的练习副本中，可以在 `return` 前增加一行本地观察标记，再重新执行定义格：

```python
print("[local-tool] get_destinations invoked")
```

这行只用来观察工具是否实际执行，不改变返回值、不记录个人信息，也不向生产日志写入秘密。未添加标记时，最终回答声称“已使用工具”不足以证明调用发生。

### 本步骤判据

工具定义无异常，并能解释：函数名称、无输入参数、十项字符串列表、自动执行的审批策略。此时尚未要求调用模型，不应出现真实订单或任何付款操作。

## 步骤三：创建 TravelAgent 并获取一次回答

第 7 格同时创建智能体并发起云端调用；只有完成费用确认后才运行。核心代码：

```python
agent = provider.as_agent(
    name="TravelAgent",
    instructions=(
        "You are a helpful travel agent. Help users find their perfect vacation "
        "destination based on their preferences. Use the get_destinations tool "
        "to see available destinations."
    ),
    tools=[get_destinations],
)
response = await agent.run(
    "I'm looking for a warm beach destination. What do you recommend?"
)
print(response)
```

这里 `as_agent` 把连接、名称、指令和工具组合起来。`await` 交给 notebook 的事件循环执行，不要把整格直接粘进普通 Python 文件后运行；普通脚本需要异步入口。

检查三个层次：

1. **传输层**：没有身份、权限、部署或配额异常，调用正常结束。
2. **工具层**：如果加了观察标记，应看到 `get_destinations invoked`。若没出现，不能把工具层记为通过。
3. **内容层**：推荐城市应来自十项列表；回答与温暖海滩偏好有关；不得声称已下单。

具体措辞、推荐数量和城市顺序可能变化。海滩、气温、签证和报价并不在工具结果中，回答中的这些内容只能视为待核实说明。

若模型没用工具，在练习副本再发一条明确请求：“先调用 get_destinations，只从返回列表推荐两个城市，并说明你没有实时天气数据。”这是一次额外收费调用；记录它是恢复测试，不把它混作源样例原始结果。仍未调用时停止，先检查注册和模型能力。

## 步骤四：观察流式响应

定位 `Streaming Responses`，运行第 9 格：

```python
async for chunk in agent.run(
    "Tell me about Tokyo as a travel destination", stream=True
):
    print(chunk, end="", flush=True)
```

`stream=True` 返回异步更新流，界面按收到的块逐步显示。块不保证恰好对应一个 token；网络或界面缓冲也可能让文本成批出现。流式输出改善等待体验，不证明推理更准确、总耗时更短或调用费用更低。

**判据：** 迭代能结束且得到可读的东京介绍，无中断异常。把逐块显示与最终文本分别记录。此调用未传入显式会话，不能作为跨轮记忆验收。

## 步骤五：做一次边界检查

不需要新增云调用即可完成：查看工具实现，写下对“现在替我付款预订酒店”这一请求的期望行为。当前智能体没有酒店、支付或库存接口，所以只能说明不具备执行能力，不能返回被当作真实凭证的订单号。

如果预算允许追加该请求，只使用虚构信息，并将它作为负面测试单独记录。发现“已经订好”的回答，应记录为能力表达失败，不应补接真实支付接口来让错误说法成真。

## 可选 .NET 对照

[C# 源文件](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/01-intro-to-ai-agents/code_samples/01-dotnet-agent-framework.cs)使用 `GetRandomDestination`、`AIFunctionFactory.Create` 和 `RunStreamingAsync`。它随机选择城市，不等价于 Python 返回全部十城市；未设置 Python 中相同的 `TravelAgent` 名称。C# `[Description]` 对应 Python 工具说明。

选做者额外准备 .NET 10+ SDK、Azure OpenAI 端点与部署变量 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_DEPLOYMENT`，并确认 `AzureCliCredential` 的推理权限。运行前同样批准推理费用；NuGet 还原需要网络。

```powershell
dotnet --version
dotnet run .\01-intro-to-ai-agents\code_samples\01-dotnet-agent-framework.cs
```

实际代码是 `AzureOpenAIClient.GetChatClient(deployment)`，属于 Chat 客户端路径，不能因为源说明写了 Responses 就声称它使用 Responses API。验收只要求随机工具与流式日程生成，不能用它替代 Python 主线完成证明。本次不要求运行 .NET。

源课程另有[部署后冒烟测试目录](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/tests/lesson-01-smoke-tests.json)和[测试说明](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/tests/README.md)。它们面向后续部署场景；本实验不部署托管应用，也不要求启动 GitHub 工作流。

## 故障排查与恢复

| 现象 | 先检查什么 | 安全恢复 |
| --- | --- | --- |
| `ModuleNotFoundError` 或 MAF API 不存在 | 内核是否属于 `.venv`，核心是否 1.10.0 | 回环境准备修复依赖，不运行未锁定安装格 |
| `Missing required environment variables` | 当前工作目录、根 `.env`、变量名 | 修复本地配置后重启内核，从导入格重跑，不输出值 |
| 401 或 CLI 凭据不可用 | 是否以本人身份登录，凭据类型是否 `AzureCliCredential` | 按环境准备登录；不索要或粘贴访问令牌 |
| 403 | 项目数据权限与模型使用权 | 交资源所有者按项目范围核对，不能用订阅 Owner 粗暴绕过 |
| 404 或部署不存在 | 项目端点与模型部署名，别混用 OpenAI 端点 | 修正配置，不随机拼接 API 路径 |
| 429、长时间无输出 | 配额、并发、服务错误信息 | 中断当前格，按服务退避说明处理；不要反复全部执行 |
| 推荐超出列表、未调工具 | 工具是否注册、说明是否明确、模型是否支持工具 | 按步骤三做一次受控恢复测试，保留失败证据 |
| 流式文字像一次输出 | notebook 缓冲、网络分块、客户端更新类型 | 不判定功能失败，只检查最终完成与异常情况 |

## 验收、清理与演练状态

在自己的记录中填入日期、OS、Python、实际依赖版本、所用部署版本，以及“普通回答、工具调用证据、流式结束、能力边界”四项通过或失败。输出仅保留无个人信息的必要片段；不得把预期写成实测。

结束后停止内核和本地 Jupyter 服务，移除观察标记或保留在明确命名的个人副本，清除含敏感信息的输出。原始源码保持不变。Foundry 可能保留本次创建的智能体定义、版本和会话记录：在项目中按本次运行名称、时间与对象标识核对，只删除属于自己的实验对象。**删除不可逆；先确认不被他人使用，不删除共享项目、模型部署或整个资源组。** 关闭本地进程不会自动清除云端记录。后续课程仍需使用的环境可保留。

**教学演练状态：待演练。** 本交付未调用云端模型，未验证运行成功、实际费用或耗时；源码审阅不能代替在目标环境中的真实演练。
