# 用内存知识库验证检索、复查与有据回答

## 学习目标与准备

本实验先检查一个真实但简单的关键词检索器，再运行普通 RAG 智能体和 maker-checker 智能体。验收重点是工具到底查到了什么、模型是否遵守资料边界、预算与季节是否同时成立，不是回答篇幅或检索次数。

先完成[环境准备](00-setup.zh-CN.md)与[Agentic RAG 概念](05-concepts.zh-CN.md)。主线使用 Windows、PowerShell 7、Python 3.12+、固定源码及 `.venv` 内核。需要 Foundry 项目、支持工具调用的模型、`AZURE_AI_PROJECT_ENDPOINT`、`AZURE_AI_MODEL_DEPLOYMENT_NAME`，代码凭据为 `DefaultAzureCredential`。

**主线不需要 Azure AI Search、Storage、嵌入部署或上传文件。** 只使用内存中的四条旅行字符串。模型调用仍会收费，多轮复查可能比一次回答用更多 token。执行前确认项目范围权限和预算；只使用公开演示资料，不上传私人文档。平台不会运行 notebook。

本地路径 `05-agentic-rag\code_samples\05-python-agent-framework.ipynb`，对应[固定版本 Python 源码](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/05-agentic-rag/code_samples/05-python-agent-framework.ipynb)。以下单元格编号含 Markdown。

## 步骤一：初始化主线

在源码根检查：

```powershell
Test-Path .\05-agentic-rag\code_samples\05-python-agent-framework.ipynb
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
```

期望为 `True`、`1.10.0`。打开 notebook 并选 `.venv` 内核，**跳过第 3 格未锁定安装命令**，使用根 `requirements.txt`。

运行第 4 格导入、`dotenv.load_dotenv()` 与变量检查，再运行第 5 格 `FoundryChatClient` 创建。变量为空先检查 notebook 工作目录与根配置是否被找到，不输出 `.env`。`DefaultAzureCredential` 不一定使用 CLI 身份，首次调用前请确认实际身份来源。

## 步骤二：阅读知识库与检索逻辑

定位 `Creating a Search Tool`，第 8 格包含 `TRAVEL_KNOWLEDGE_BASE` 与 `search_travel_knowledge(query)`。先逐条阅读四条资料：

| 目的地 | 最佳季节 | 日均费用（演示美元） | 资料中的部分亮点 |
| --- | --- | --- | --- |
| Barcelona | Mar-May 或 Sep-Nov | 150–200 | Gaudí architecture、La Rambla、beaches |
| Tokyo | Mar-Apr 或 Oct-Nov | 200–250 | Shibuya、temples、sushi |
| Paris | Apr-Jun 或 Sep-Oct | 180–250 | Eiffel Tower、Louvre、cuisine |
| Cape Town | Nov-Mar | 100–150 | Table Mountain、wine regions、wildlife |

函数按目的地名称或描述中的任意查询词子串匹配，返回带城市标题的字符串；没有结果时返回：

```text
No matching destinations found in the knowledge base.
```

它没有向量化、搜索评分、日期解析或真实价格查询。先明确这些限制，再运行第 8 格定义。

## 步骤三：不调用模型，验证真实检索算法

下面是可选的本地检查，在源码根 PowerShell 中运行。它只从 notebook JSON 的第 8 格提取字典和函数 AST，移除框架装饰器后执行相同函数体；不执行导入配置格，不读取 `.env`，不创建客户端或调用模型。它验证的是检索算法，不是 MAF 集成。

```powershell
@'
import ast
import json
from pathlib import Path
from typing import Annotated

path = Path(r"05-agentic-rag\code_samples\05-python-agent-framework.ipynb")
notebook = json.loads(path.read_text(encoding="utf-8"))
tree = ast.parse("".join(notebook["cells"][7]["source"]))
selected = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "TRAVEL_KNOWLEDGE_BASE"
        for target in node.targets
    ):
        selected.append(node)
    if isinstance(node, ast.FunctionDef) and node.name == "search_travel_knowledge":
        node.decorator_list = []
        selected.append(node)
assert len(selected) == 2, "源码结构已变化，请停止并核对版本"
module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
scope = {"Annotated": Annotated}
exec(compile(module, str(path), "exec"), scope)
search = scope["search_travel_knowledge"]
assert "**Barcelona**" in search("architecture")
assert "**Tokyo**" in search("Tokyo")
assert search("April") == "No matching destinations found in the knowledge base."
assert "**Barcelona**" not in search("Apr")
assert all(f"**{name}**" in search("") for name in scope["TRAVEL_KNOWLEDGE_BASE"])
print("本地检索算法断言通过；未调用云端模型。")
'@ | .\.venv\Scripts\python.exe -
```

最后一行是预期成功输出，不是此前演练记录。若断言失败，先核对 SHA 与单元格内容，不为了通过而修改断言。

这些断言刻意暴露限制：完整 `April` 无结果、`Apr` 不理解区间、空查询返回全部。下一步观察模型能否用目的地名称或合适关键词恢复，而不是假定检索器已经具备语义理解。

## 步骤四：观察 TravelRAGAgent 的首次检索

为得到真实工具证据，在个人练习副本 `search_travel_knowledge` 函数的 `return` 前加入：

```python
print(f"[retrieval] query={query!r}; matched={len(results)}")
```

重新执行第 8 格工具定义，再执行 `Building the RAG Agent` 下第 10 格。只记录固定测试查询，不在真实敏感数据上无差别记录全文。

智能体指令的四条要求是：先查知识库、基于检索结果回答、缺资料明确说明、提供费用季节和亮点。原请求询问擅长建筑的目的地。

```python
response = await agent.run(
    "I'm interested in visiting somewhere with great architecture. What destinations would you recommend?",
)
print(response)
```

**验收：**

1. 有实际 `[retrieval]` 观察记录，不能仅看模型自称查过。
2. 若查询 `architecture`，知识库直接支持 Barcelona 及 Gaudí 建筑，相关费用与季节应按资料转述。
3. 模型若推荐额外城市，应能指出检索依据；不能凭训练知识扩展后仍说所有结论都来自知识库。
4. 没有检索到签证、天气和实时航班，不能作确定性承诺。

工具格式只含城市标题与文本，没有稳定文档 ID 或引文接口。回答提及城市不等于已经实现正式引用追踪。

## 步骤五：观察 Maker-checker 复查

定位 `Iterative Retrieval — The Maker-Checker Pattern`，运行第 12 格。它创建 `TravelRAGCheckerAgent`，要求先查候选、逐个按目的地再查、比较已核实信息、资料不足时再次确认。

原问题为每天 175 美元预算、四月出行。检查工具日志里是否有初始检索及后续按目的地名称的查询；若没有复查，应记录为未观察到该模式，不用模型文字“我已 double-check”替代证据。

### 正确比较预算与时间

- Tokyo：四月在所列季节，但日均 200–250 超预算。
- Paris：四月在所列季节，但日均 180–250 超预算。
- Cape Town：100–150 符合预算，但 Nov-Mar 不包含四月。
- Barcelona：Mar-May 包含四月，150–200 包含 175，但上限高于预算，不能保证所有费用都不超标。

合格回答可以说“没有由现有资料保证完全符合的选项”，或把 Barcelona 作为需压低开支并再核实的折中；不能说四个条件都已严格满足。最佳季节并不意味着其他月份禁止旅行，只是本题按知识库条件筛选，模型应说明区分。

只会重复相同查询、始终没有新证据时应停止，不无限重试。当前源码没有显式最大迭代控制，课堂操作要人工监控，异常时中断单元格。

## 步骤六：检验缺失资料与语言边界

预算允许时追加一个补充请求，例如“根据知识库说明 Barcelona 的签证费用；如果没有资料，请明确说明。”这会增加一次模型调用。预期先检索，再承认资料不包含签证费用，不能引用城市日均费用充当签证费。

中文查询与月份缩写问题优先用步骤三的本地方法理解，避免为每个变体反复调用模型。主线使用英文提示是为了对应英文知识库和源代码，不表示课堂解释必须使用英文。若改用中文提示，应单独记录是否进行了查询翻译或改写，不能假定检索器自动支持中文同义词。

## 可选 Azure AI Search 索引路线

[固定版本 AzureSearch.md](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/00-course-setup/AzureSearch.md)是独立扩展，主线完成不依赖它。指南涉及 Storage、Search 服务、索引、上传文档与 Python/.NET SDK。创建资源、索引和上传是额外行动，**先批准资源费用、数据驻留、最小权限和清理责任**；不能把“免费层可用于测试”当作订阅一定可用或完全无费用的承诺。

如果已有独立实验 Search 服务，先完成以下审查再行动：

1. 由所有者提供 `AZURE_SEARCH_SERVICE_ENDPOINT`；确认不是 Foundry 项目端点。
2. 索引创建与管理需要适用的 `Search Service Contributor`，文档写入需要 `Search Index Data Contributor`；只查询应使用更小的读权限。角色分配由获授权管理员操作，不申请订阅 Owner。
3. 优先 Entra/RBAC；源指南密钥回退需要管理密钥而非 query key，须经安全渠道处理，不能贴进 notebook 输出。
4. 使用自己专属且不会覆盖他人的索引名；源码默认 `sample-index` 可能与已有索引冲突。先检查归属，不能为消除冲突直接删除同名索引。
5. 源 Python 片段的 `edm` 导入及 `SimpleField(... searchable=True)` 应按实际 `azure-search-documents` 核对；用于可搜索字符串字段的当前常见写法如下，属于本手册兼容性提示，不是已演练结果：

```python
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType,
)
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
]
```

创建与上传后，需检查每个上传结果成功，并执行已知词查询确认能找回文档。再将 `search_travel_knowledge` 的内存实现替换为查询独立索引的函数，同时保留无结果、错误、结果限量和来源信息；**只建索引并不会自动连接当前 notebook**。源指南的两个文档是 Hello world 与 Azure Cognitive Search，不是四城市知识库，也没有完整向量字段或嵌入流程。

可选索引清理应先删自己创建的索引或数据，再核对是否仍需独立服务和 Storage；只删索引不一定停止 Search 服务计费。未创建 Storage 的直接 SDK 上传路线不需要凭空建立或删除 Storage。删除前确认数据备份及共享依赖，不执行资源组级批量删除。

## 可选 .NET 文件检索路线

[05 C# 文件](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/05-agentic-rag/code_samples/05-dotnet-agent-framework.cs)、[.NET notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/05-agentic-rag/code_samples/05-dotnet-agent-framework.ipynb)和[document.md](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/05-agentic-rag/code_samples/document.md)是另一套实现，不是 Python 内存检索的语言直译。

实际流程：`PersistentAgentsClient` 上传 `document.md` 为 `demo.md`，创建向量存储，创建带 `FileSearchToolDefinition` 的 `DotNetRAGAgent`，通过 `GetAIAgentAsync` 和 `GetNewThread` 查询 Contoso 旅行保险。资料只说明保险覆盖医疗急救、行程取消和行李丢失等，不含一般神经网络知识。

**额外风险先决条件：** 该路线会向云端上传文件、创建持久智能体、向量存储和会话，产生模型及可能的文件存储/检索费用；需相应上传、管理和删除权限。源代码用早期预览包，必须先核对服务与包兼容性，不应升级一部分包后期待原 API 仍可用。

本次将其列为待单独演练路线，默认只阅读代码。选做执行前必须补上对象标识记录与清理方案，避免上传成功后失败却遗留数据。若选 file-based `.cs` 路线，使用 .NET 10+；若选 notebook，需 C#/.NET Interactive 内核，不能在 Python 内核运行。

路径也要预先修正理解：源代码 `./document.md` 要求工作目录在 `05-agentic-rag\code_samples`，而 `Env.Load("../../../.env")` 从那里会越过仓库根，不能假定能读取正确配置。应在受控终端预先配置批准的环境变量，并在个人副本纠正或移除这一加载行；不要读取上级目录不属于实验的环境文件。

验收应包括：上传文档可检索、保险回答仅涵盖文件内容、无关问题明确拒答、引文可核对。代码没有显式索引就绪等待与清理，因此不能声称天然完成所有企业监控、权限过滤、混合检索、备份与容灾功能。清理需按本次标识依次核对会话、智能体、向量存储和上传文件；部分成功也要清理，删除不可逆且不能影响共享对象。

## 故障排查

| 现象 | 排查与恢复 |
| --- | --- |
| 缺少环境变量 | 检查当前目录与 dotenv 加载，不展示实际配置；修复后重启内核 |
| 401/403 | 核对 `DefaultAzureCredential` 身份链及项目数据权限，不能把 Search 角色当作模型角色 |
| `April` 查不到 | 先用本地断言验证缩写限制，再按城市名查完整资料 |
| 中文查询没有资料 | 源检索是英文子串匹配；改写查询或选读本地算法，不把无结果归因于云故障 |
| 空查询或常见词返回过多 | 给输入增加边界与查询规范化的设计，记录源算法限制 |
| 有资料仍推荐超预算 | 检查数值范围与季节逻辑，不能仅按工具调用成功判定答案正确 |
| 反复查询、429 | 中断当前格，检查是否重复参数、配额与退避，不开启无界重试 |
| 可选 Search 建索引报导入错误 | 先核对 SDK 字段类型与版本，不能在主线里追加无关服务修复 |
| 可选 .NET 上传后无结果 | 核对文件路径、服务 API、索引就绪及对象标识；先防止重复上传 |

## 验收、清理与演练状态

主线应交付四项记录：本地检索算法边界、建筑问题的工具与答案证据、预算季节复查表、缺资料时的诚实回答。没有实时云执行的项写“未执行”，不要填入假想工具版本、输出或耗时。

清理时关闭内核和 Jupyter，移除个人副本的观察日志或去敏保存。内存知识库随内核消失，不需要删除 Search 索引。Foundry 中按本次 `TravelRAGAgent`、`TravelRAGCheckerAgent`、时间和标识核对对象，再删除仅属本实验的智能体及会话。**删除前确认归属、共享依赖与保留要求；不删除共享模型、项目、整个资源组。** 可选 Search 和 .NET 路线的额外资源分别按上文清理。

源课程另有[05 部署后冒烟目录](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/tests/lesson-05-smoke-tests.json)，适用于另行部署后的基础检查，不是本地主线的必需步骤，也不等于完整 RAG 质量评估。

**教学演练状态：待演练。** 本交付不声称已完成云调用、文件上传、索引配置、.NET 运行或部署。静态源码核对与离线算法检查不替代真实教学环境演练。
