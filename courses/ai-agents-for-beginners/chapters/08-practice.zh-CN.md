# 实作顺序、并行与条件协作工作流

## 目标与统一准备

本章覆盖主旅行工作流以及基础交接、家具报价、并行旅行规划和条件出版四个 Python 变体；另对照有意义的 .NET 实现。完成后，应能检查图结构、输出执行者和真实消息依赖，而不是仅阅读概念。

先完成[环境准备](00-setup.zh-CN.md)和[多智能体概念](08-concepts.zh-CN.md)。Windows PowerShell 7、Python 3.12+，固定 `agent-framework-core==1.10.0`。从源码根打开 VS Code，使用 `.venv`，为每个 notebook 重启独立内核；索引从 JSON `cells[0]` 开始。

**费用与权限提示：任何 `agent.run` 或 `workflow.run` 都可能触发多次收费模型请求。并行不会减少调用数量。只使用获批开发项目，不连接生产；后文条件变体还涉及搜索、远端代码执行和文件写入，默认只做离线路由练习。**

### 分支资源不能混用

| 路线 | 实际客户端 | 必要配置与限制 |
| --- | --- | --- |
| 主 Python、Workflow Python 01/02/03 | `FoundryChatClient` | `AZURE_AI_PROJECT_ENDPOINT`、`AZURE_AI_MODEL_DEPLOYMENT_NAME`；项目模型与实验智能体权限 |
| .NET 主例和 Workflow 01/02/03 | `AzureOpenAIClient.GetChatClient` | `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_DEPLOYMENT`、Azure OpenAI 数据权限；不是 Foundry 项目端点 |
| Workflow Python 04 | `agent_framework.azure.AzureAIAgentClient` 等旧接口 | 原代码要求 `BING_CONNECTION_ID`，另依赖旧集成环境；当前锁定环境兼容性未确认 |
| Workflow .NET 04 | `PersistentAgentsClient` | `AZURE_AI_PROJECT_ENDPOINT`、`BING_CONNECTION_ID`，模型写死 `gpt-5-mini`；会创建三个持久智能体 |

Bing 是整门课的可选路线，但选中原条件样例后并非可以留空：Python 索引 9 直接索引 `os.environ["BING_CONNECTION_ID"]`，.NET 无条件构造 grounding 配置。它需要资源所有者提供已配置连接与预算，不是填一个名称就自动创建服务。

## 步骤一：主旅行工作流从两阶段扩展到三阶段

打开[08-python-agent-framework.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/08-python-agent-framework.ipynb)，本地路径为 `08-multi-agent\code_samples\08-python-agent-framework.ipynb`。

1. 索引 2 将安装、导入与配置混在一格。在学习副本注释掉 `%pip install agent-framework ...` 那一行，再执行其余导入和变量检查；不要整格跳过必要导入。
2. 运行索引 3 创建 `FoundryChatClient`，索引 6 创建 `planner_agent` 和 `concierge_agent`。
3. 检查角色：`TravelPlanner` 负责日程和行程，`TravelConcierge` 补充本地建议、餐厅与遗漏，不互相复制职责。
4. 运行 `Building a Sequential Workflow` 下索引 8，源码图结构为：

```python
workflow = WorkflowBuilder(start_executor=planner_agent) \
    .add_edge(planner_agent, concierge_agent) \
    .build()
```

输入是五天、巴黎、喜爱美食的两人、预算 3000 美元。代码通过 `workflow.run(..., stream=True)` 遍历事件，仅显示 `event.type == "output"` 且 `event.data` 为 `AgentResponseUpdate` 的文本，并按 `author_name` 分组。

验证：图中有一条 Planner 到 Concierge 的边；最终可见输出回应了原请求，并包含审阅或增强内容。流式输出过滤器不保证显示所有内部步骤，缺少某个作者标题不能单凭肉眼认定该节点没运行；应结合图和事件类型排查。

5. 运行索引 10，创建 `BudgetReviewer` 与第二条边，再执行一次。比较新增输出是否针对预算指出成本项、风险和节省建议。

源码没有实时价格工具、真正订票或付款。预算表是模型估计；三阶段更长不等于更准确。记下有证据支持的改进，也记下遗漏，不能宣称固定性能提升。

## 步骤二：基础交接与可视化

源码：[01.python-agent-framework-workflow-ghmodel-basic.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/python/01.python-agent-framework-workflow-ghmodel-basic.ipynb)。

本地目录为 `08-multi-agent\code_samples\workflows-agent-framework\python`。文件名保留 `ghmodel`，但实际代码已经用 Foundry，不需要 GitHub Models token。

1. 按索引 2–9 运行导入、加载配置、`provider`、FrontDesk/Concierge 指令和建图。索引 1 安装语句已注释，保持不执行。
2. 索引 10 的 `WorkflowViz(workflow).to_mermaid()` 和 `to_digraph()` 提供图文本。查看起点与边即可，不要求安装 Graphviz。
3. SVG 导出依赖可选 Python 包和系统 Graphviz；没有时跳过索引 10 中的 `viz.export` 与索引 12 的显示逻辑。平台章节不导入 SVG 或原始 HTML。
4. 预算允许后运行索引 13：

```python
events = await workflow.run("I would like to go to Paris.")
outputs = events.get_outputs()
result = outputs[0].text if outputs else ""
```

预期 `outputs` 非空，末端 Concierge 给出批准或改进意见。这里只从输出执行者取最终结果，不应期待 `get_outputs()` 返回整个内部对话。索引 14 的 `replace("None", "")` 只是文本替换，不是错误恢复；不要用它遮掩缺失结果。

## 步骤三：家具三阶段报价

源码：[02.python-agent-framework-workflow-ghmodel-sequential.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/python/02.python-agent-framework-workflow-ghmodel-sequential.ipynb)。

1. 独立内核执行索引 2–10，核对 `Sales-Agent → Price-Agent → Quote-Agent` 两条边。
2. 可视化索引 11/13 与基础例一样，只需图文本。不要为了显示图安装未锁定扩展。
3. **跳过索引 14**：它读取 `../imgs/home.png` 并构造 `image_uri`，但当前 Python 后续并未使用该 URI。运行索引 15 的 `message`，其内容明确列出三座沙发、两把扶手椅、木茶几、电视柜、落地灯和地毯。
4. 运行索引 16，使用 `events.get_outputs()` 取 Quote-Agent 最终文本。

验收按三层检查：家具清单覆盖文本要求；价格阶段区分预算、中档与高档并考虑配送、组装等费用；报价阶段有清晰项目与估算总额。价格没有商家检索依据，只能称估算。

这个 Python 变体不是视觉识图实验，虽然旧教程和未使用的图片读取仍保留。下文 .NET 02 才实际把图片字节送给模型，不要混报能力。

## 步骤四：并行分发不等于顺序依赖

源码：[03.python-agent-framework-workflow-ghmodel-concurrent.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/python/03.python-agent-framework-workflow-ghmodel-concurrent.ipynb)。

索引 2–6 配置 Foundry、研究员与规划员。索引 7 定义真正的分发器：

```python
class InputDispatcher(Executor):
    @handler
    async def forward(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.send_message(text)
```

建图使用 `WorkflowBuilder(start_executor=dispatcher, output_executors=agents).add_fan_out_edges(dispatcher, agents).build()`，不是配套 README 中的 `ConcurrentBuilder`。

1. 运行至索引 7，检查 dispatcher 同时连向两个角色，两个角色之间没有边。
2. 只读索引 8 的图文本；不要求 SVG。
3. 控制并发预算后运行索引 10、11。输入为 “Plan a trip to Seattle in December”。
4. 检查输出数量是否覆盖两个预期角色，内容分别体现研究和规划。不要依靠完成先后猜角色身份，也不要把并列文本当作已消除矛盾的综合计划。

`PlanAgentInstructions` 说依据研究结果，但图并没有把研究结果送给它。这是很好的反例：提示不能创造数据依赖。新增离线设计任务是画一个“研究与预算并行 → 汇总 → 规划”的图，明确汇总输入契约；不必再次调用模型。

## 步骤五：条件出版的真实边界与离线分支验证

源码：[04.python-agent-framework-workflow-aifoundry-condition.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/python/04.python-agent-framework-workflow-aifoundry-condition.ipynb)。

**先停在只读模式：不要执行索引 1 的 `agent-framework-azure-ai -U`，也不要执行索引 13 的完整云端块。** 该例保留 `AzureAIAgentClient`、`create_agent`、无参 `WorkflowBuilder().set_start_executor(...)`、`workflow.run_stream` 等旧 API，不能用升级主环境的方式强行兼容。注释所称 `Installation` 文件也不是已交付的锁定环境依据。

实际流程：

1. `EvangelistInstructions` 要求按提纲和链接写超过 200 词的稿件。
2. `ContentReviewerInstructions` 要求返回 `review_result`、`reason`、`draft_content`。
3. 索引 10 的 `to_reviewer_result` 用 `ReviewAgent.model_validate_json` 解析，再发出 `ReviewResult`。
4. `select_targets` 将 Yes 路由到 `save_draft`，其他情况到 `handle_review`。
5. `save_draft` 本身不写文件，只转发 `AgentExecutorRequest`；真正预期写文件的是带 `HostedCodeInterpreterTool` 的 publisher。
6. No 分支输出审查失败，没有回到起草者的边。“直到合格再重写”只是提示愿望，不是实现。

在独立学习 notebook 复制源码的 `ReviewResult` 数据类和 `select_targets` 函数即可做离线检查，不导入旧云客户端：

```python
from dataclasses import dataclass

@dataclass
class ReviewResult:
    review_result: str
    reason: str
    draft_content: str

def select_targets(review: ReviewResult, target_ids: list[str]) -> list[str]:
    handle_review_id, save_draft_id = target_ids
    if review.review_result == "Yes":
        return [save_draft_id]
    else:
        return [handle_review_id]

targets = ["handle_review", "save_draft"]
assert select_targets(ReviewResult("Yes", "test", "synthetic draft"), targets) == ["save_draft"]
assert select_targets(ReviewResult("No", "too short", "short"), targets) == ["handle_review"]
assert select_targets(ReviewResult("Unexpected", "invalid", ""), targets) == ["handle_review"]
```

此检查只证明路由函数，不证明旧 SDK、Bing 或 publisher 可用。列出待修订要求：恰好 200 词的政策、严格 JSON 输出、有限修订循环、发布前人工批准、发布产物标识与清理。

Python 索引 9 虽创建 `BingGroundingTool(connection_id=conn_id)`，后面的 agent 实际传入的是 `HostedWebSearchTool()`，并未直接使用变量 `bing`；因此“连接已绑定搜索”不能只凭环境变量存在推断。publisher 写出的文件也可能位于托管环境，而非你的源码目录。

## 可选 .NET：逐例对照而非混用 Python API

以下 `.cs` 文件均有同名 `.md`；Workflow 子目录还保留同名 `.ipynb`。file-based `.cs` 需 .NET 10+；Interactive notebook 需单独的 .NET 内核，不能在 Python 内核运行。

| 固定源码 | 对照操作与验收 |
| --- | --- |
| [08-dotnet-agent-framework.cs](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/08-dotnet-agent-framework.cs) | 找到 `FrontDesk`、`Concierge`、`AddEdge`，跟踪 `TurnToken` 和 `AgentResponseUpdateEvent`；它不是 Python 主例的三角色预算链 |
| [01.dotnet-agent-framework-workflow-ghmodel-basic.cs](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/01.dotnet-agent-framework-workflow-ghmodel-basic.cs) | `GetChatClient().AsIChatClient().AsAIAgent` 创建角色，`RunStreamingAsync` 运行；按执行者核对文本，不把拼接输出当完整 trace |
| [02.dotnet-agent-framework-workflow-ghmodel-sequential.cs](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/02.dotnet-agent-framework-workflow-ghmodel-sequential.cs) | `OpenImageBytesAsync` 读取 `../imgs/home.png`，`DataContent(imageBytes, "image/png")` 实际传图；需视觉模型和获准上传的合成室内图片 |
| [03.dotnet-agent-framework-workflow-ghmodel-concurrent.cs](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/03.dotnet-agent-framework-workflow-ghmodel-concurrent.cs) | `ConcurrentStartExecutor` 广播消息和 turn token；`AddFanInBarrierEdge` 汇合；`ConcurrentAggregationExecutor` 加锁并等到两条消息才输出 |
| [04.dotnet-agent-framework-workflow-aifoundry-condition.cs](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/04.dotnet-agent-framework-workflow-aifoundry-condition.cs) | `DraftExecutor`、`ContentReviewExecutor`、`GetCondition`、`PublishExecutor`、`SendReviewExecutor` 构成条件图；拒绝只输出通知，不自动重写 |

### .NET Interactive notebook 的独立入口

以下四份是原始 notebook 的固定版本入口，不是 `.cs` 文件的别名。先在 .NET 内核中阅读对应单元格；依赖、身份、预算和下节兼容性条件未确认时，不执行包恢复或云调用。尤其不要运行条件例中直接显示连接标识的索引 7。

| 原始 notebook | 关键单元格与对照任务 |
| --- | --- |
| [01.dotnet-agent-framework-workflow-ghmodel-basic.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/01.dotnet-agent-framework-workflow-ghmodel-basic.ipynb) | 索引 17 创建两角色，18 建图，20–21 启动与收集流；核对 `TurnToken` 和 `ExecutorId`，判断收集的是哪些角色片段 |
| [02.dotnet-agent-framework-workflow-ghmodel-sequential.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/02.dotnet-agent-framework-workflow-ghmodel-sequential.ipynb) | 索引 17 读图片、20 连接三角色、21 构造 `DataContent`、22–23 运行；确认图像输入与 Python 当前文本输入不同，跳过索引 18 的原始字节展示 |
| [03.dotnet-agent-framework-workflow-ghmodel-concurrent.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/03.dotnet-agent-framework-workflow-ghmodel-concurrent.ipynb) | 索引 16 定义分发与汇总执行者，18 用旧 `AddFanInEdge`，19 用旧 `StreamAsync`；与 `.cs` 的 barrier 与新运行入口逐项对照，不直接互换 |
| [04.dotnet-agent-framework-workflow-aifoundry-condition.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/08-multi-agent/code_samples/workflows-agent-framework/dotNET/04.dotnet-agent-framework-workflow-aifoundry-condition.ipynb) | 索引 16 创建持久智能体，24–28 定义执行者，29 定义 `GetCondition`，32 建分支，39–40 运行；只读追踪 Yes/No 路径，确认没有自动修订回边 |

### 版本与运行门槛

01/02/03 及主例的 NuGet 使用浮动版本；04 则固定在旧 preview.251001.3 与 Persistent beta 包。Python 的 1.10.0 约束不约束这些 NuGet。先由接收方确认兼容 SDK 和具体依赖，固定学习副本并记录版本；本次不承诺它们已经编译成功。

尤其 03 的 `.ipynb` 仍用 `AddFanInEdge` 和 `InProcessExecution.StreamAsync`，而 `.cs` 已是 `AddFanInBarrierEdge` 和 `RunStreamingAsync`；不要把两份代码拼起来运行。01/02 的流式拼接在切换执行者时可能漏掉切换当次片段，文本不完整时先检查收集逻辑，不能直接判定模型遗漏。

批准的 .NET 01/02/03 实验在 `08-multi-agent\code_samples\workflows-agent-framework\dotNET` 目录执行，例如：

```powershell
dotnet --version
Test-Path ..\imgs\home.png
dotnet run .\01.dotnet-agent-framework-workflow-ghmodel-basic.cs
```

最后一条会恢复依赖并调用收费模型，只有版本与预算已确认才运行。源码 `Env.Load("../../../.env")` 按这个工作目录并不指向仓库根；不要把秘密复制到多个层级，使用获准的进程环境或在学习副本明确正确配置路径。

### 条件 .NET 的额外风险

04 会调用 `Administration.CreateAgentAsync` 创建 Evangelist、ContentReviewer、Publisher，绑定 Bing grounding 和 Code Interpreter。**创建前必须明确模型 `gpt-5-mini` 的真实部署、权限、搜索和托管计算费用、远端文件保留政策，以及由谁删除创建的对象。** 原代码没有对应清理块，且使用旧 API；本课程不执行这一云端变体。

其 `ExtractJson` 通过首尾花括号取稿件 JSON，不是普适解析器；审核失败、无效 JSON 和边界词数都应作为待演练用例。无需云端，也能手工给 `GetCondition` 的 Yes/No 输入画出两条路径。

## 故障处理与清理

| 现象 | 排查与恢复 |
| --- | --- |
| 文件名写 ghmodel，却找不到 GitHub token | 01/02/03 已改 Foundry；按实际客户端配置，不申请无关 token |
| 图导出失败 | 保留 `to_mermaid()`、`to_digraph()` 文本；跳过 SVG，不影响学习图结构 |
| 图片路径失败 | Python 02 可跳过未使用读取；.NET 02 必须检查工作目录与真实 PNG，不上传私宅或个人照片 |
| 没有预期输出 | 检查 `get_outputs()`、输出执行者和事件过滤；空结果不能用替换 `"None"` 掩盖 |
| 并行分支失败或 429 | 先停运行，降低并发并记录缺失分支；没有自定义恢复就不能声称其余分支自动容错 |
| 条件例 import/API 报错 | 保留为兼容性阻塞，做离线路由练习；不要执行浮动升级或混装旧 Azure 集成 |
| .NET 汇总不再输出 | 检查 `_messages.Count == 2` 与是否重复复用同一 aggregation 实例；新增角色须同步修改汇合与计数设计 |

结束时停止内核或 `.NET` 进程。仅删除自己本轮导出的图和学习输出，先核对文件名，不用通配符清空目录。不得把 SVG、真实图片、完整对话或秘密复制进课程包。主线无真实预订或采购；Foundry 可能保留实验智能体/会话，按本轮对象标识交由资源所有者清理，不删共享项目。

若接收方另行演练条件云端变体，需登记三个 agent ID、会话、代码解释器文件等实际产物，先保留去敏验收证据，再逐项删除获准删除的对象；不能把本地 `finally: print("done")` 当作清理完成。

**教学演练状态：待演练。** Python 主线、四变体和 .NET 分支分别记录“已运行／未执行／兼容性阻塞”；本次仅做源码对照和本地文件检查，没有部署、搜索、代码解释器或云模型调用。
