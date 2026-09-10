# 验证清晰指令、结构化结果与单一职责

## 学习目标与准备

本实验不是简单查看三段模型回答，而是分别验证：指令与实际能力是否一致、结构化结果是否真的通过类型解析、两个角色是否遵守职责边界。结合[人本设计原则](03-concepts.zh-CN.md)，完成后应能指出至少一个源样例的能力缺口，并给出可测试的改进方案。

按[环境准备](00-setup.zh-CN.md)完成 Windows、PowerShell 7、Python 3.12+、固定源码和 `.venv`。需要 Foundry 项目端点及模型部署变量，模型应支持当前 SDK 所用工具调用与结构化输出。代码使用 `DefaultAzureCredential`，即使已 `az login`，也应确认凭据链没有选择非预期身份。

**运行前风险提示：** 主线包含多次模型请求，两个角色的串行运行增加推理费用。所有预算、季节和可用性来自演示字典或模型知识，不是实时旅游报价。不要依据签证建议作真实出行决定，也不要输入真实姓名、证件或支付信息。无权限时请资源所有者核对项目范围授权，不扩大到整个订阅。

源文件：[03 Python notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/03-agentic-design-patterns/code_samples/03-python-agent-framework.ipynb)，本地路径 `03-agentic-design-patterns\code_samples\03-python-agent-framework.ipynb`。编号包含所有 Markdown 单元格。

## 步骤一：准备且只运行必要单元格

```powershell
Test-Path .\03-agentic-design-patterns\code_samples\03-python-agent-framework.ipynb
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core')); print(version('pydantic'))"
```

预期文件存在，核心为 `1.10.0`；Pydantic 实际版本如实记录，不假定已经演练过某一组合。打开文件，选择 `.venv` 内核，**跳过第 3 格未锁定的安装命令**，使用根 `requirements.txt` 管理依赖。

运行第 4 格导入、变量检查及客户端初始化。它读取 `AZURE_AI_PROJECT_ENDPOINT` 和 `AZURE_AI_MODEL_DEPLOYMENT_NAME`，并构造 `FoundryChatClient(..., credential=DefaultAzureCredential())`。若缺配置，在本地修复后再继续，不展示配置值。

## 步骤二：运行清晰指令，检查过度承诺

定位 `Pattern 1: Clear Agent Instructions`，第 6 格创建 `TravelConcierge`，角色名为 Alex，要求：

- 理解预算、气候和活动偏好；
- 推荐前检查目的地可用性；
- 给出详细个性化建议；
- 提到签证要求和最佳季节，保持热情专业语气。

执行原请求：一周假期、喜欢美食和历史、预算约 2500 美元。观察回答结构、是否回应天数与预算、是否指出信息不足。

**关键检查：** 这个 `as_agent` 没有 `tools=`。它无法真正查询库存、实时酒店或签证政策。若回答说“我已经检查过可用性”，把它记为透明度失败，而非工具功能成功。不要让“高质量人设”掩盖没有证据的问题。

在纸面写一条改进指令，例如“没有库存工具时明确说明无法核实，不要声称已预订”。若需要 A/B 比较，只在个人副本新建一个不同名称的智能体，改变这条指令，保持原请求一致；这属于额外收费测试，不修改固定源样例或伪装原始结果。

## 步骤三：运行结构化推荐

定位 `Pattern 2: Structured Output with Pydantic Models`。第 8 格包含模型定义、工具、智能体构造、调用与输出，按顺序整体执行。

工具 `get_destination_details` 的已知结果：

| 目的地 | available | best_season | estimated_budget_usd | highlights |
| --- | --- | --- | --- | --- |
| Barcelona | True | May-Jun | 2000 | Beach、Architecture、Nightlife |
| Tokyo | True | Mar-Apr | 2500 | Culture、Food、Technology |
| Cape Town | False | Nov-Mar | 1800 | Nature、Wine、Adventure |
| 未知目的地 | False | Unknown | 0 | 空列表 |

实际调用中，结构化约束由这一参数开启：

```python
response = await structured_agent.run(
    "Recommend 3 destinations for a culture-loving traveler with a $2500 budget",
    options={"response_format": TravelRecommendations},
)
```

`DestinationRecommendation` 是单条结果，`TravelRecommendations` 是外层推荐数组加 `personalized_note`。只声明这两个类而不把格式交给运行调用，不足以保证响应是对应结构。

### 检查类型结果，再检查业务内容

在第 8 格之后新增一个补充检查格，不产生新的模型调用：

```python
assert response is not None, "没有返回响应对象"
assert isinstance(response.value, TravelRecommendations), "未得到已解析的结构化结果"
result = response.value
print(result.model_dump())
assert len(result.recommendations) > 0, "推荐数组为空"
for rec in result.recommendations:
    assert rec.estimated_budget_usd >= 0, "预算不能为负"
```

这里 `len > 0` 只是最低检查；用户要求三项，应另记录实际数量是否为三。不要在类型验证通过后就宣告满足预算、偏好和事实。

逐条对照上表：已知城市的可用性、季节和预算应与工具一致；未知城市的预算 `0` 表示缺数据，不能解释成免费旅行；Cape Town 可以作为“不可用的比较项”，不能作为可立即预订方案。`personalized_note` 应解释文化偏好及限制。

如果响应走到原样例的 `No validated structured response was returned.` 分支，结构化验收未通过。保留错误类别，检查模型是否支持结构化输出和 SDK 参数，不把自由文本手工改成 JSON 后声称原调用通过。

## 步骤四：运行两个单一职责角色

定位 `Pattern 3: Single Responsibility Agents`，执行第 10 格。

- `DestinationExpert` 注册 `get_destination_details`，负责评价、查可用性、给简短排序，明确不谈航班和酒店。
- `LogisticsPlanner` 没有工具，负责选定目的地的逐日行程、航班酒店建议、签证与保险提示，明确不重新推荐目的地。

实际交接方式是：

```python
dest_response = await destination_agent.run(
    "I want a week of culture and food for under $2500. Where should I go?"
)
logistics_response = await logistics_agent.run(
    f"Plan a week-long trip based on this recommendation:\n{dest_response}"
)
```

它传递第一位的文字结果，不自动传递一个经过业务校验的行程对象，也没有显式把原始预算再次加入第二条请求。检查第一位的输出是否保留预算约束，第二位是否继承它、是否擅自改变目的地，以及是否把未经查询的航班酒店当成已确认事实。

在记录中标注哪一条边界失败，不因第二位回答更长而认为协作更好。改进时可用明确交接字段保存目的地、预算、日期、数据来源和待核实事项，但这属于扩展设计，本次主线不要求实现新编排框架。

## 步骤五：完成透明度与控制评审

不用再调用模型，直接检查源代码：

1. 是否有展示 AI 身份或信息局限的固定界面？哪些只是提示要求？
2. 是否存在保存、查看、删除用户偏好的函数？当前 Python 样例没有。
3. 哪个智能体真的注册了工具，哪个只能生成建议？
4. 用户说“停止”时，本地执行和服务端对象如何处理？提示词不能代替应用取消机制。

将答案写入本次验收记录，区分“设计要求”“已有代码”“未实现”。这一步使原则评审不依赖模型偶然表现。

## 可选 .NET 实践

[实际 C# 源文件](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/03-agentic-design-patterns/code_samples/03-dotnet-agent-framework.cs)使用 .NET 10+ file-based app、Azure OpenAI 两个环境变量和 `AzureCliCredential`。需另行批准推理费用；源文件浮动 NuGet 版本须记录实际还原版本。

```powershell
dotnet run .\03-agentic-design-patterns\code_samples\03-dotnet-agent-framework.cs
```

按输出依次观察 `Hello`、`I prefer luxury travel and cultural experiences.`、`Suggest a destination for me.` 三轮。关注工具 `SaveUserPreference` 的 `[TRANSPARENCY]` 日志，以及 `GetRandomDestination` 是否尊重明确目的地优先原则。

`SaveUserPreference` 只打印和返回字符串，并未持久化；第三轮利用的是共享会话中的信息。指令要求修改偏好前确认，但代码没有独立审批机制，因此需要把“是否先确认”当作行为测试，不能声称有强制审批。当前文件使用 `GetChatClient`，不是仅凭 README 的 Responses 标签即可认定的 Responses 实现。

对应 [.NET 说明文档](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/03-agentic-design-patterns/code_samples/03-dotnet-agent-framework.md)包含更多架构模式介绍，但展示的代码与实际 `.cs` 有差异。功能判断以 `.cs` 为准；本实验不要求实现全部企业模式。

## 故障排查

| 现象 | 排查与恢复 |
| --- | --- |
| 导入失败或 API 参数报错 | 检查内核和核心 1.10.0，跳过旧安装格，不升级全套依赖试错 |
| `DefaultAzureCredential` 链失败或 403 | 核对实际身份来源、项目端点与数据角色；CLI 登录不保证被选中 |
| 格式未解析，`response.value` 为空 | 确认运行调用含 `options`、模型支持当前结构化能力，保留原始异常类别 |
| 返回三项但包含未知城市或 0 美元 | 查工具默认分支；0 不是免费报价，标记缺失数据 |
| Cape Town 被标成可预订 | 对照工具中的 False，记录事实一致性失败 |
| 第二位忘记预算或换地方 | 检查交接文本，而非假定两个智能体共享完整用户请求 |
| 多次执行生成太多对象或 429 | 停止全部重跑，按失败单元格恢复，先检查配额和现有对象 |

## 验收、清理与演练状态

主线结果包括三份证据：一份“指令与工具能力”差异说明、一份类型与业务双层结构化检查、一份角色交接评审。记录真实日期、OS、Python、依赖和模型部署版本；只保留去敏内容。

关闭内核和 Jupyter，清理个人副本输出。云端核对本次 `TravelConcierge`、`StructuredTravelExpert`、`DestinationExpert`、`LogisticsPlanner` 及对应会话，按对象标识确认归属后再删除。**删除前确认不被他人使用；不要删除共享模型、项目或资源组。** 未完成调用也可能留下部分对象，不能只按“最后成功的名称”查找。若做了 .NET 选做，还应检查其服务保留记录；它没有真实偏好数据库需要删除。

**教学演练状态：待演练。** 尚未进行真实模型、结构化响应或 .NET 运行验证；本章明确列出预期判据与已知源码限制，不能据此填报成功。
