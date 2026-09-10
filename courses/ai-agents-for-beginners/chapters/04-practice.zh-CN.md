# 组合旅行工具并检查结构化输出与审批边界

## 学习目标与准备

本实验验证三个只读工具的选择和参数，识别源 notebook 结构化输出部分漏传格式参数的问题，并检查审批元数据与真实审批闭环的区别。完成后应能用代码和观察记录证明哪些工具执行过，而不是只复述模型的自述。

先完成[环境准备](00-setup.zh-CN.md)与[工具调用原理](04-concepts.zh-CN.md)。环境为 Windows、PowerShell 7、Python 3.12+、固定提交及 `.venv` 内核。Foundry 主线需要 `AZURE_AI_PROJECT_ENDPOINT`、`AZURE_AI_MODEL_DEPLOYMENT_NAME` 和支持工具/结构化输出的部署。源码使用 `DefaultAzureCredential`，须核对实际身份链。

**风险提示：** 执行模型格会计费，组合工具可触发多次往返。目的地、余位、航班与价格都为静态演示，不能用于真实购买。`book_flight` 只生成模拟文字，不接真实支付；不要把它替换为真实业务 API 后继续使用未经验证的示例流程。任何写入、付款或删除都必须先有授权、审批和幂等设计。

主线文件 `04-tool-use\code_samples\04-python-agent-framework.ipynb`，对应[固定版本 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/04-tool-use/code_samples/04-python-agent-framework.ipynb)。编号包含 Markdown 格。

## 步骤一：初始化客户端

```powershell
Test-Path .\04-tool-use\code_samples\04-python-agent-framework.ipynb
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
```

应为 `True` 和 `1.10.0`。打开 notebook，**跳过第 3 格未锁定的 `-U` 安装命令**；依赖遵循根 `requirements.txt`，不要执行全部单元格。运行第 4 格配置检查和第 5 格 `FoundryChatClient` 构造。

配置为空时停下，在本地修复后重启内核。不要展示 `.env` 内容或凭据。客户端创建成功不代表模型权限已验证。

## 步骤二：定义并检查三个只读工具

定位 `Defining Tools with the @tool Decorator`，运行第 7 格。

| 工具 | 输入 | 数据与边界 |
| --- | --- | --- |
| `get_destinations` | 无 | Barcelona、Paris、Berlin、Tokyo、Sydney、New York City |
| `check_availability` | 城市名称 | Berlin 为 `Sold out`；Barcelona 剩 3 个，Tokyo 剩 1 个；未知键返回 `Unknown destination` |
| `get_flight_info` | 出发与到达机场代码 | 仅有 LHR-BCN、LHR-CDG、LHR-NRT 三条静态航线 |

两个重要测试区分：

- 城市名 `Barcelona` 用于可用性函数，机场码 `BCN` 用于航班函数，不能互换。
- `No direct flights ...` 是字典没有记录的默认文本，不能作为全球航班市场不存在直飞的证明。

如需观察真实调用，在个人练习副本的三个函数体开头分别加如下标记，然后重新执行定义格：

```python
# 放在 get_destinations 的函数体内
print("[tool] get_destinations")
# 放在 check_availability 的函数体内
print(f"[tool] check_availability({destination!r})")
# 放在 get_flight_info 的函数体内
print(f"[tool] get_flight_info({origin!r}, {destination!r})")
```

不要把三行一起加进同一个函数；标记中的变量必须属于对应函数参数。仅用固定演示数据，避免日志记录个人信息。

## 步骤三：组合工具回答库存问题

执行 `Creating an Agent with Multiple Tools` 下第 9 格：

```python
travel_tools = [get_destinations, check_availability, get_flight_info]
agent = client.as_agent(
    name="TravelToolAgent",
    instructions="You are a travel agent. Use the available tools to answer questions about destinations, availability, and flights.",
    tools=travel_tools,
)
response = await agent.run(
    "What destinations do you have? Which ones are still available?"
)
print(response)
```

验收时查工具标记：应获取目的地并检查可用性；回答不能把 Berlin 列为可预订，不能虚构目的地列表。原问题没问航班，模型不调用 `get_flight_info` 并非错误；工具越多调用越多并不是目标。

若未查可用性就回答，先确认函数注册和内核顺序，再在预算允许时追加一个明确测试：“Use check_availability for Berlin and Barcelona, then report the exact status.” 这属于恢复调用，须与原始调用分开记录。

## 步骤四：验证结构化输出并补足源样例缺口

定位 `Structured Output with Tools`，阅读第 11 格。它声明：

```python
class BookingRecommendation(BaseModel):
    destination: str
    available: bool
    flight_details: str
    estimated_cost: int

class TravelPlan(BaseModel):
    recommendations: list[BookingRecommendation]
```

**已知源码差异：第 11 格创建了 `StructuredTravelAgent`，但 `structured_agent.run(...)` 没有传入 `response_format`，只打印回答。** 因此按原格运行只能检验普通响应，不能据此声称得到验证后的 `TravelPlan`。

为避免多付一次模型调用，可以在个人副本保留模型与智能体定义，将该格最后的调用和输出替换为以下补充版本；原始源码不改动，并在记录中注明本手册补充了格式参数：

```python
response = await structured_agent.run(
    "I want to fly from London Heathrow to somewhere warm in Europe. "
    "Check what's available.",
    options={"response_format": TravelPlan},
)
assert response is not None, "没有响应"
assert isinstance(response.value, TravelPlan), "没有已验证的 TravelPlan"
plan = response.value
print(plan.model_dump())
```

这与模块 03 已使用的 `options={"response_format": ...}` 形式一致；是否被当前部署完整支持仍须真实演练。若已经运行原格，以上是额外一次收费调用，而不是原格的成功证明。

### 双层验收

**结构层：** `response.value` 应是 `TravelPlan`；数组存在，每项具备四个字段。`estimated_cost` 为整数并不自动限制币种、非负或总预算。

**业务层：** 对照本地静态航线：

| 航线 | 源样例文本 |
| --- | --- |
| LHR-BCN | BA 2042，08:30 出发，11:45 到达，$350 |
| LHR-CDG | AF 1081，09:15 出发，11:30 到达，$280 |
| LHR-NRT | JL 044，11:00 出发，次日 07:00 到达，$890 |

应使用机场代码查询，不能把未支持航线说成已确认。原请求“欧洲且温暖”需要模型判断，但工具没有气象字段；推荐理由应标明此限制。`estimated_cost` 不能无依据扩展为含酒店、餐饮、税费的完整行程总价。

如果需要明确航线测试，在预算允许时询问“Check Barcelona availability and the LHR to BCN flight.” 验证参数与 $350 记录一致，而不是强制自然语言全文相同。

## 步骤五：检查审批工具，而不是执行真实预订

定位 `Tool Approval Patterns`，运行第 13 格。它定义 `book_flight(origin, destination, passenger_name)`，设置 `approval_mode="always_require"`，然后打印：

```python
print("Tool name:", book_flight.name)
print("Approval mode:", book_flight.approval_mode)
```

期望元数据表示工具名 `book_flight` 和 `always_require`。没有模型调用，也没有实际订单。

用源代码确认三件事：

1. `book_flight` 没有加入上面的 `travel_tools` 或两个智能体。
2. notebook 没有处理审批请求、拒绝和恢复运行的代码。
3. 函数的“确认号”由 `hash(passenger_name)` 派生，非稳定、非真实订单凭证。

本实验验收只包括审批策略声明，不要求绕过审批直接调用函数，不宣称已验证人工在环。将来扩展时要设计确认界面、审批绑定到最终参数、拒绝后无副作用、重复请求幂等和超时后的状态核查。

## 可选 .NET 多工具对照

[04 C# 源文件](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/04-tool-use/code_samples/04-dotnet-agent-framework.cs)真正包含四个工具：`GetRandomDestination`、`GetWeather`、`GetDestinationInfo`、`EstimateTripCost`。不要用对应 Markdown 里旧的单随机工具代码判断当前功能。

选做需 .NET 10+、Azure OpenAI 端点与部署变量、本人 CLI 推理权限及预算；浮动 NuGet 版本要如实记录。

```powershell
dotnet run .\04-tool-use\code_samples\04-dotnet-agent-framework.cs
```

三个演示依次询问东京天气、罗马五天豪华旅行成本、随机目的地三天中等预算完整计划。函数自带 `[Tool Called]` 日志，可核对：

- 东京天气静态记录为 Sunny、24°C，并非当前天气。
- 罗马五天豪华成本：住宿 `500*5=2500`、餐饮 `250*5=1250`、活动采用整数除法 `(500/3)*5=830`，合计 4580。
- 工具组合应该使用所需参数，但模型无需为简单天气问题调用全部工具。

未知天气会返回约 20°C 的演示默认值；未知目的地信息会返回通用赞美语，这些都不是有依据的检索结果。成本函数没有检查负天数，也不能宣称已完成生产输入验证。C# 实际是 `GetChatClient` 路线，非仅凭标题即可认定的 Responses API。

源目录的 [test_demo_plugins.py](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/04-tool-use/code_samples/test_demo_plugins.py)引用仓库未提供的 `demo_tool_agent`，且测试旧 Time/Calculator 插件，不是当前旅行工具验收器。本实验不要求运行它，更不能把它当成本次工具测试已通过的证据。

## 预期结果与验收

主线通过应同时具备：目的地与可用性工具的真实执行证据；Berlin 售罄等静态事实被正确转述；补充格式调用得到 `TravelPlan` 而非只有自由文本；审批格仅验证 `always_require` 元数据，并明确没有真实预订或完整审批对话。四项分别记录，某一项通过不能抵消另一项失败。

## 故障排查、清理与演练状态

| 失败现象 | 排查与处理 |
| --- | --- |
| 结构化格只得到文本 | 原格漏传格式；使用标明的补充版本，不把文本伪装为类型通过 |
| 机场代码无匹配 | 检查 `LHR`、`BCN` 等大小写和参数位置，不把城市名传给机场码 |
| Berlin 仍被推荐为可预订 | 对照 `Sold out`，核查工具调用及模型转述，记录事实错误 |
| 401/403 | 核对 `DefaultAzureCredential` 选择的身份及项目数据权限 |
| 429/长时间循环 | 中断当前格，限定候选与问题，按配额和退避要求恢复 |
| 找不到旧测试插件模块 | 这是源补充测试缺依赖，不要凭空安装同名第三方包 |
| 没出现审批对话框 | 本 notebook 只定义工具并打印元数据，没有审批执行流程 |

记录主线调用、格式补充、审批元数据和选做路线各自的结果，含实际版本与去敏证据。失败不得被“模型最后回答了”掩盖。

清理本地内核、Jupyter 和个人副本观察标记；核对 Foundry 中本次 `TravelToolAgent`、`StructuredTravelAgent` 及会话对象。**删除前按标识确认归属和依赖，删除不可逆；不删除共享模型、项目、资源组。** 本实验没有真实订单需要取消，也没有数据库或航班服务资源需要删除。

源课程另提供[04 部署后冒烟目录](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/tests/lesson-04-smoke-tests.json)，只在另行部署后使用，本主线不部署、不运行工作流。

**教学演练状态：待演练。** 未进行模型调用、人工审批、C# 执行或订单写入；源代码差异和补充步骤均已明确区分。
