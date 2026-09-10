# 实践会话偏好存储与 Cognee 图谱记忆

## 目标与执行边界

本章先用 Python 主 notebook 比较同会话、新会话和外部字典，再修正工具注册并观察偏好读写。可选部分使用 Cognee 图谱，让搜索工具成为真正可调用的记忆接口。每一步都要求存储与调用证据，不以模型自述为准。

先完成[环境准备](00-setup.zh-CN.md)与[记忆概念](13-concepts.zh-CN.md)。环境为 Windows、PowerShell 7、Python 3.12+，核心 SDK 为 `agent-framework-core==1.10.0`，源码固定 `25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595`。

### 在运行前确认费用、权限与数据边界

- 主线需要 Foundry 项目、已部署的工具调用模型及项目级访问/实验智能体管理权限；使用 `DefaultAzureCredential`。它不需要 Mem0、Azure AI Search、Redis 或外部记忆 API。
- 主线“酒店搜索”是静态列表，没有真实订单；禁止接真实付款、医疗或客户数据。
- Cognee 额外需要 `cognee[redis]==0.4.0`、Redis、独立 LLM/嵌入服务配置与预算，并使用 `AzureCliCredential` 访问 Foundry。构图、`memify` 和图检索可能多次调用付费服务。
- Cognee 单元格 8 的 `prune_data()` 与 `prune_system(metadata=True)` 是删除操作。必须先改为自己的专用数据目录，初次练习跳过这两句；绝不能在已有共享存储上“全部运行”。
- 使用合成用户 `lab_user_13`，不把源码中的演示姓名、健康描述或联系方式替换为真实个人资料。提交作业只含计数、合成 ID 和判据。

## 步骤一：复制与核对主 notebook

来源：[会话与字典记忆 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/13-agent-memory/13-agent-memory.ipynb)。

工作目录为源码仓库根；已有目标文件时先检查，勿覆盖：

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
New-Item -ItemType Directory -Force .\lab-work\13 | Out-Null
Copy-Item .\13-agent-memory\13-agent-memory.ipynb .\lab-work\13\13-memory.ipynb
```

预期 SHA 与上述固定值一致，核心包为 `1.10.0`。在副本选择 `.venv` 内核，跳过原单元格 3 的未约束安装。单元格编号从 1 开始且包含 Markdown；以函数名辅助定位。

顺序运行单元格 4、5，分别导入/校验配置和创建 `FoundryChatClient`。配置对象创建成功不等于已完成云端验证。

## 步骤二：建立会话寿命的对照组

执行单元格 8：`TravelMemoryAgent` 在同一个 `session` 中接收海滩偏好和 3000 美元预算，再被询问预算。

预期第二次回答能准确复述预算且不增添无来源事实。接着运行单元格 10，新建 `new_session` 后再问预算。预期它承认不知道或请求补充；即使碰巧猜到 3000，也不能算它读取了旧会话，代码没有提供旧历史。

记录：

| 组别 | 输入中包含什么 | 判定 |
| --- | --- | --- |
| 同一会话 | 本次及前两轮消息 | 应能解释预算来自哪一轮 |
| 新会话 | 只有新问题和智能体指令 | 不应声称知道未提供的预算 |
| 重启内核后 | 无先前 Python 对象 | 不得假定 session 或字典仍存在 |

暂时不要重启，因为下一步还需要客户端；重启对照放在字典观察之后。

## 步骤三：修正工具注册，再验证读写链

### 识别真实后端

单元格 12 定义 `preference_store: dict[str, list[str]] = {}`，并提供：

- `save_preference(user_id, preference)`：追加字符串；
- `get_preferences(user_id)`：返回该 ID 的全部已保存偏好；
- `search_hotels(query)`：从五家静态酒店的名称、地点或标签查子串。

这个字典在同一内核不同会话间共享，但重启就丢失。源码所谓“weeks later”只模拟新会话，并没有真的跨进程保存数周。

### 只在副本补齐缺失工具

单元格 14 的原始 `tools` 仅包含保存和读取工具，指令却要求调用 `search_hotels`。将该参数改为：

```python
tools=[save_preference, get_preferences, search_hotels]
```

同时把该单元格指令中固定用户 ID 改为 `lab_user_13`，保持每个记忆操作使用相同合成 ID。将原始人物场景改为合成旅行描述，例如：

```python
session_1 = travel_agent.create_session()
response = await travel_agent.run(
    "This is a synthetic lab trip. Remember that I prefer quiet, accessible "
    "hotels and cultural destinations. My budget is at most 800 USD per night. "
    "Please save the preferences, search the sample hotels, and do not book.",
    session=session_1,
)
print(response)
```

先执行修改后的 `travel_agent` 创建代码，再执行调用。没有重新创建智能体时，单改工具列表文字不会改变内核里的旧对象。

在三个工具的副本函数体开头增加只打印函数名称的日志，重新运行定义和创建单元格。预期观察到读取偏好、保存偏好、酒店搜索的调用证据。`save_preference` 可能被模型拆分成多次调用，因此不要求恰好存入固定条数。

### 检查存储而不是信任回答

在新单元格中只输出合成 ID 的计数和检查结果：

```python
prefs = preference_store.get("lab_user_13", [])
assert prefs, "没有保存偏好；先检查工具调用"
print({"user_id": "lab_user_13", "preference_count": len(prefs)})
```

本地屏幕人工核对是否保存了安静、无障碍、文化与预算，是否添加了用户没说的条件。实际应用还必须去重、支持更正并校验事实；当前源码只追加，没有这些机制。

随后再提供一个新偏好，要求记住，并在新会话中询问推荐：

```python
await travel_agent.run(
    "Also remember that I prefer public transport. This is synthetic data.",
    session=session_1,
)
session_2 = travel_agent.create_session()
response = await travel_agent.run(
    "Use my saved preferences to recommend one sample hotel. Explain what "
    "information remains unverified; do not invent accessibility guarantees.",
    session=session_2,
)
print(response)
```

预期新会话调用 `get_preferences`，并使用保存事实而不是要求全部重述。无障碍设施、价格和饮食适配仍必须向真实服务核实；样例标签不支持做安全保证。

## 步骤四：识别搜索与身份边界

`search_hotels` 使用整段查询的子串匹配，不是向量检索，也不会解析“便宜且无障碍”的多条件表达式。无匹配时直接回退前三家；其中存在每晚 850 美元、可能超过本次 800 美元预算的酒店。

因此“工具返回了酒店”不等于“酒店符合约束”。做两次对照：

1. 短查询 `accessible` 可匹配具有该标签的条目。
2. 不存在的合成标签应被识别为检索无可靠匹配，不能把回退列表描述为精准命中。

在副本改善此行为的最小设计是：无匹配返回空结果，并在推荐前对 `price <= budget` 做确定性过滤。将过滤后的数量与理由记入作业；不要把语义相似度或模型口头承诺当成硬预算校验。

另检查 `user_id`：示例把它固定在指令中便于教学，但任何真实应用都不能信任模型传入的身份。应由已认证会话绑定主体，在工具实现中强制用户范围。用第二个合成 ID 设计隔离反例，要求检索不到第一人的记录；本例不具备生产级多租户授权。

## 步骤五：做真正的持久化最小练习

下面是本手册扩展，不是源码自带的 Mem0/Search 实现。它用 JSON 文件证明“跨进程恢复”需要显式保存。只在自己的 `lab-work\13` 使用合成数据；已有文件时先核对：

```python
import json
from pathlib import Path

cwd = Path.cwd().resolve()
repo = next(p for p in (cwd, *cwd.parents) if (p / "13-agent-memory").is_dir())
memory_file = repo / "lab-work" / "13" / "synthetic-preferences.json"
if memory_file.exists():
    raise FileExistsError("先检查自己的记忆文件，不要覆盖")
memory_file.parent.mkdir(parents=True, exist_ok=True)
memory_file.write_text(
    json.dumps({"lab_user_13": preference_store.get("lab_user_13", [])}, ensure_ascii=False),
    encoding="utf-8",
)
print({"saved": memory_file.is_file()})
```

在源码根另开 PowerShell，启动独立 Python 进程读取；不要把全文打印到交付记录：

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; p=Path('lab-work')/'13'/'synthetic-preferences.json'; d=json.loads(p.read_text(encoding='utf-8')); assert d.get('lab_user_13'); print({'loaded_in_new_process':True,'count':len(d['lab_user_13'])})"
```

预期新进程能读取非空记录。再重启 notebook 内核：旧 `preference_store` 不存在，重新运行原定义后为空。只有显式从文件加载，工具才会得到保存的记录。该文件方案仍没有加密、并发写、索引、删除传播或访问控制，不能作为生产存储。

## 可选路线：Cognee 图谱记忆

### 环境与额外服务

来源：[Cognee notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/13-agent-memory/13-agent-memory-cognee.ipynb)。

为避免可选依赖影响主线，可在源码根新建独立环境。安装会联网，先确认软件来源与预算：

```powershell
py -3.12 -m venv .venv-cognee
.\.venv-cognee\Scripts\python.exe -m pip install -r requirements.txt "cognee[redis]==0.4.0"
.\.venv-cognee\Scripts\python.exe -m pip check
.\.venv-cognee\Scripts\python.exe -c "from importlib.metadata import version; print(version('cognee')); print(version('agent-framework-core'))"
Copy-Item .\13-agent-memory\13-agent-memory-cognee.ipynb .\lab-work\13\13-cognee.ipynb
```

预期版本分别为 `0.4.0`、`1.10.0`，且依赖检查无冲突。其他依赖并未全部锁定；如果解析失败，保留冲突报告并停下，不自动放宽框架约束。

源 notebook 要求 Redis 和 `CACHING=true`，并读取 `LLM_API_KEY`。该密钥用于 Cognee 配置的模型后端，不等同于 Azure CLI 的 Foundry 身份。还须确认 Cognee 的生成模型与嵌入模型使用哪个提供商、模型、端点和凭据；不能仅设置 Foundry 两变量就假设图谱服务可用。

若使用经批准的 Docker Desktop，可在**没有同名容器**时启动仅本机可访问的演示 Redis：

```powershell
docker run --name lab13-redis --detach --publish 127.0.0.1:6379:6379 redis:7
docker exec lab13-redis redis-cli ping
```

预期 `PONG`。记录 Redis 实际版本与镜像摘要；`redis:7` 不是不可变镜像标识。本机 6379 被占用时不要停止他人服务，应由环境负责人给出专用 Redis 配置。默认裸 Redis 无生产认证，本章不开放公网、不挂载共享数据。

### 先改存储边界，再构图

在副本选择 `.venv-cognee` 内核，跳过单元格 3 的安装。运行 4、5 前确认配置只含批准的服务。单元格 8 改为使用自己的 `lab-work\13` 子目录，并**删除或注释掉副本中的两句 prune 调用**：

```python
cwd = Path.cwd().resolve()
repo = next(p for p in (cwd, *cwd.parents) if (p / "13-agent-memory").is_dir())
DATA_ROOT = repo / "lab-work" / "13" / "cognee-data"
SYSTEM_ROOT = repo / "lab-work" / "13" / "cognee-system"
DATA_ROOT.mkdir(parents=True, exist_ok=True)
SYSTEM_ROOT.mkdir(parents=True, exist_ok=True)
cognee.config.data_root_directory(str(DATA_ROOT))
cognee.config.system_root_directory(str(SYSTEM_ROOT))
```

这段只配置目录。已有图谱时先核对，不反复执行摄取造成重复数据与费用。

运行单元格 10 准备三类合成素材，单元格 11 调用 `add` 与 `cognify`：

| 素材 | NodeSet | 应能检索的内容 |
| --- | --- | --- |
| 开发者技术背景 | `developer_data` | FastAPI、Pydantic、asyncio |
| 历史问答 | `developer_data` | 并发控制、异步测试、日志 |
| Python 原则 | `principles_data` | 显式优于隐式、命名和结构 |

先观察构图是否完成和错误类型，再选择执行 `memify()`；它是额外模型处理，不是必跑的免费显示步骤。

图谱可视化单元格 13 应把输出路径改到 `lab-work\13\cognee-graph.html`。它只供本机检查节点和边，**不是平台导入资源**；不要把 HTML 作为图片、附件链接或原始 HTML 嵌入课程。

### 修正工具接入与提问

单元格 17 的 `search_knowledge` 和 `search_principles` 已实现 `cognee.search`，但单元格 18 未传入工具。副本创建 `coding_agent` 时补上：

```python
tools=[search_knowledge, search_principles]
```

`search_principles` 通过 `NodeSet` 和 `node_name=["principles_data"]` 缩小检索范围。可在两个函数中增加只打印函数名与结果是否为空的日志，不输出整段私人资料。

原始第一问提到 `AsyncWebScraper`，但摄取内容没有该类的实现，不能声称模型审查了真实代码。将第一问改为“根据图谱中的历史问答，异步抓取为何需要并发上限？”；再问“Python 原则对命名有什么建议？”。

预期前者实际调用 `search_knowledge`，后者调用 `search_principles`；答案与摄取材料对应。新建 `session_2` 后再次查询仍应通过图谱工具检索。仅同内核的新会话成功不能证明跨重启持久化；重启后需重新配置相同存储、创建工具/智能体，且不执行 prune 或重复摄取，再做独立恢复测试。

## 其他记忆后端的有意义扩展

Mem0 与 Azure AI Search 在 README 中是架构选项，不是当前主 notebook 的运行依赖。扩展设计应保留 `save_preference/get_preferences` 的业务契约，后端负责主体过滤、版本、失效与删除；Mem0 需观察提取/更新行为，Search 需定义字段、过滤器、嵌入及索引权限。

白板可沿用[上一模块便签实践](12-practice.zh-CN.md)，保存当前任务状态而非所有长期偏好。将三种后端用“跨重启、跨用户隔离、更新、更正、遗忘、延迟、费用”七项比较，写出未完成项；不要安装多个收费后端只为得到同一句聊天回答。

## 故障处理与结果判定

| 现象 | 排查与恢复 |
| --- | --- |
| 新会话没有偏好 | 核对合成 ID、工具注册、字典是否被重新初始化、检索是否真的调用 |
| 回答说搜过但无调用 | 重新创建补齐工具的智能体；Cognee 与主 notebook 都有缺失工具注册点 |
| 重启后记忆全空 | 字典本就不持久；Cognee 检查目录、后端配置与是否执行了 prune |
| Cognee 401/模型错误 | 独立检查 Cognee 生成与嵌入提供商，不把 Foundry CLI 登录当成其密钥 |
| Redis 连接失败 | 先确认专用实例、地址、端口与缓存配置；不要开放公网或停掉共享实例 |
| 图谱能查到但事实错误 | 核对源材料、节点范围与派生规则，隔离错误记忆，不用重试掩盖 |
| SDK 导入失败 | 核对内核与版本；可选环境冲突不应通过升级主环境解决 |

主线验收需要三组会话寿命对照、工具注册修正、存储计数、检索证据、预算/搜索边界说明和新进程读取结果。Cognee 可选验收需要构图、过滤检索、工具调用与新会话记录，不用生成的赞许文字代替证据。

## 演练状态与清理

当前状态为**待演练**。本次仅审阅本地源码，未执行 Foundry、Cognee、Redis、Mem0、Search 或正式平台校验；具体安装兼容性和恢复行为均待批准环境演练。

结束前确认删除范围。关闭 notebook 内核与自己启动的 Redis；仅删除本次命名容器：

```powershell
docker stop lab13-redis
docker rm lab13-redis
```

未启用 Redis 路线则不运行上述命令。删除容器会丢失其未持久化缓存，但不会自动清除图谱文件或外部模型服务数据。不要使用 `docker system prune`、全局 Redis 清空或 Cognee 全局 prune。

在源码根用 `Get-ChildItem .\lab-work\13` 核对自己的 JSON、图谱目录与 HTML，再对明确路径使用 `Remove-Item -WhatIf` 预览，确认后删除。保留去敏结果表；外部后端如有数据，按其删除与保留政策清理，不能把本地文件删除当成云端遗忘完成。
