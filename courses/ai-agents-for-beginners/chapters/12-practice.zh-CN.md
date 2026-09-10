# 实践会话摘要、外部便签与上下文检查

## 目标、版本与风险

完成后应能证明同一会话保留偏好、日期修订生效、摘要工具被调用，并区分“生成摘要”与“真正减少下一次输入”。再用自己的本地便签把已确认状态传入新会话，验证信息保留与原始历史排除。

先完成[环境准备](00-setup.zh-CN.md)与[上下文概念](12-concepts.zh-CN.md)。环境为 Windows、PowerShell 7、Python 3.12+，`agent-framework-core==1.10.0`；主线使用 `FoundryChatClient` 与 `DefaultAzureCredential`，不是 notebook 前言遗留文字所说的直接 Azure OpenAI 路线。

**执行前风险提示：** 每个 `agent.run` 都可能产生模型费用；摘要也可能增加调用次数，并非免费优化。使用已批准的 Foundry 项目与模型部署，确认项目级数据权限。便签写盘会保存用户状态，本实验只允许合成资料，不能写健康信息、票号、真实日历或凭据。最后删除文件前要确认是自己的练习文件，不删除仓库原有便签。

## 步骤一：准备独立工作区

来源：[固定版本 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/12-context-engineering/code_samples/12-chat_summarization.ipynb)和[便签格式示例](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/12-context-engineering/code_samples/vacation_agent_scratchpad.md)。

在源码仓库根执行。目录已有作业时先检查，不覆盖：

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
New-Item -ItemType Directory -Force .\lab-work\12 | Out-Null
Copy-Item .\12-context-engineering\code_samples\12-chat_summarization.ipynb .\lab-work\12\12-context.ipynb
```

预期 SHA 为 `25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595`，核心版本为 `1.10.0`。在编辑器打开副本并选择课程 `.venv` 内核。以下编号包含 Markdown 单元格；新增代码后用函数名定位。

跳过原单元格 3 未约束的 `%pip install`。依次执行导入单元格 4 和配置单元格 5。`Microsoft Foundry client configured` 仅表示对象创建完成，不代表已验证身份、配额或模型可用。

## 步骤二：观察同一会话如何积累状态

执行单元格 8 创建 `ContextAwareAgent`，再运行单元格 10 的前三轮：

1. 日本旅行；兴趣是寿司、寺庙与摄影。
2. 预算 3000 美元，单人，四月，十天。
3. 询问最不应错过的体验。

三次调用都传同一个 `session=agent.create_session()` 创建的对象。预期第三轮回答与日本及兴趣有关，且不与预算、单人或时长冲突。输出文字不固定，不要求恰好推荐某个景点。

继续执行单元格 12：

- 第四轮补充传统日式旅馆偏好；
- 第五轮明确把四月改为十月；
- 第六轮要求总结完整计划。

用下表人工核对第六轮，不能只看“模型记忆很好”的提示文字：

| 字段 | 当前应生效值 | 常见错误 |
| --- | --- | --- |
| 目的地 | 日本 | 跟后续希腊例子混淆 |
| 预算/币种 | 3000 / USD | 变成每晚预算或无依据增长 |
| 人数与时长 | 单人 / 十天 | 变为双人或两周 |
| 时间 | 十月 | 四月仍被当作生效时间 |
| 兴趣 | 寿司、寺庙、摄影 | 只保留最近一项 |
| 住宿 | 传统日式旅馆 | 换成豪华酒店而未解释 |
| 业务状态 | 仅规划 | 声称已订房或付款 |

这证明的是会话连续性与修订处理，不是外部长期记忆。重建 `session` 后不应假设此前偏好仍在。

## 步骤三：检验摘要工具实际做了什么

单元格 14 的核心函数是：

```python
@tool(approval_mode="never_require")
def summarize_preferences(conversation_notes: str) -> str:
    """Summarize accumulated user preferences into a compact format."""
    return f"[SUMMARY] User preferences recorded: {conversation_notes}"
```

函数本身不压缩、不写文件、不计算 token；内容由模型作为参数提供。它把参数包装成工具结果，供同一会话继续使用。可以在副本函数开头增加 `print("called: summarize_preferences")` 观察调用，不打印实际备注。

执行该单元格创建 `SummarizingTravelAgent`，再运行单元格 15 的希腊场景。预期：

1. 工具被调用，内容包含希腊、海鲜、历史、跳岛、4000 美元、两周、双人、六月。
2. 后续三个岛屿建议与这些约束相关。
3. 不把之前日本会话中的十月、3000 美元混入新会话。

**不成立的结论：** “出现 `[SUMMARY]` 就代表旧消息被删除”“磁盘便签已保存”“输入 token 已下降”。源码没有任何这样的实现。工具调用和工具结果反而会加入消息；要证明压缩生效，必须检查下一次调用输入。

## 步骤四：补一个可复现的文件便签

下面是本手册的教学扩展，添加在自己的 notebook 副本末尾，不是原 notebook 已实现的功能。它使用人工核对的结构化摘要，避免把错误摘要自动写成长期事实。先重启到本章日本场景或使用下列固定合成状态，不将希腊状态混入。

### 写入已确认状态

确保内核工作目录位于自己的源码仓库根或其子目录。下面代码向上找到仓库根，并且只在自己的 `lab-work\12` 写入。若目标文件已有内容，先读取自己的文件核对；不要直接覆盖别人作业。

```python
import json
from pathlib import Path

cwd = Path.cwd().resolve()
repo = next(
    p for p in (cwd, *cwd.parents)
    if (p / "12-context-engineering" / "code_samples").is_dir()
)
scratchpad = repo / "lab-work" / "12" / "trip-state.json"
scratchpad.parent.mkdir(parents=True, exist_ok=True)
if scratchpad.exists():
    raise FileExistsError("请先检查自己的 trip-state.json，再决定是否覆盖")

state = {
    "task_id": "lab-trip-12",
    "revision": 2,
    "destination": "Japan",
    "budget_usd": 3000,
    "days": 10,
    "travelers": 1,
    "month": "October",
    "interests": ["sushi", "temples", "photography"],
    "accommodation": "traditional Japanese inns",
    "pending": ["exact dates", "city allocation"],
    "booking_authorized": False,
    "source": "synthetic turns 1-6; manually checked",
}
scratchpad.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
loaded = json.loads(scratchpad.read_text(encoding="utf-8"))
assert loaded["month"] == "October"
assert loaded["booking_authorized"] is False
assert loaded["task_id"] == "lab-trip-12"
print({"saved": scratchpad.is_file(), "revision": loaded["revision"]})
```

预期 `saved=True`、`revision=2`。这只证明本地持久化和字段验证，不证明模型曾经调用保存工具，也不提供多用户授权、加密或并发控制。

### 明确选择要注入的字段

下一次推荐不需要把整个来源说明和所有历史原句都送进模型。选择字段、记录 ID，并只传经核对的状态：

```python
import hashlib

selected = {
    key: loaded[key] for key in (
        "destination", "budget_usd", "days", "travelers", "month",
        "interests", "accommodation", "pending", "booking_authorized"
    )
}
summary_text = json.dumps(selected, ensure_ascii=False, sort_keys=True)
inspection = {
    "task_id": loaded["task_id"],
    "strategy": "manual-summary-to-new-session",
    "summary_id": "trip-summary-v2",
    "summary_sha256": hashlib.sha256(summary_text.encode("utf-8")).hexdigest(),
    "selected_field_count": len(selected),
    "summary_characters": len(summary_text),
    "raw_history_in_next_call": False,
    "redaction_status": "synthetic-only",
}
print(inspection)
```

这里 `summary_characters` 是字符数，不是模型 token 使用量；哈希只用于对比同一摘要是否变化。不要把真实偏好正文或可逆的身份字段写入日志。

### 在新会话中使用便签

确认预算后只运行一次：

```python
fresh_session = agent.create_session()
response = await agent.run(
    "Use only the following confirmed synthetic trip state as user context. "
    "Treat missing exact dates as unknown. Recommend one itinerary outline; "
    "do not book or pay. State which details still need confirmation.\n"
    + summary_text,
    session=fresh_session,
)
print(response)
```

此处使用原单元格 8 创建的 `agent`。新会话不会自动继承旧会话消息；我们显式注入摘要，保留同一个智能体的稳定指令。这演示“历史卸载到文件，下一次只提供有界状态”，不是原会话内部的自动裁剪器。

判据：输出保持十月、十天、单人、3000 美元约束；承认具体日期和城市分配未定；不宣称预订；输入构造中没有重新拼接前三轮或六轮原始聊天。模型真实 token 用量若需比较，应记录服务返回的使用量与相同任务基线，不能用上述字符数推算准确节省比例。

## 步骤五：测试选择、冲突与隔离

### 冲突和中毒反例

仅在内存副本中把 `month` 改成 `April`，或新增一个“未经验证的直飞航线”字段。先不调用模型。用 Python 断言拒绝旧修订或未验证字段：

```python
candidate = dict(loaded, month="April", revision=1)
assert candidate["revision"] < loaded["revision"]
allowed_fields = set(selected)
unverified = {"direct_flight_claim": "synthetic-unverified"}
assert not set(unverified).issubset(allowed_fields)
print("旧修订与未经验证字段应排除，不进入下一次调用")
```

这是规则练习，不会自动判断任意事实真伪。实际库存仍要有可信工具验证。合格记录应写排除原因与 ID，而不是把错误事实写入永久记忆。

### 工具选择和运行时对象

为当前“行程草案”列出只读资料查询与预算计算两个工具，明确排除订房、付款和邮箱发送。将这张白名单与 `booking_authorized=False` 联系起来：上下文可以告诉模型不要预订，真正工具层仍应拒绝写入。

把 `state` 看成运行时对象，标明哪些字段由用户确认、哪些来自工具、哪些仍为未知。若字段校验失败，应退回收集信息，不把错误字符串硬塞给模型。

### 多智能体和沙箱隔离

设计一个交通专家，只发送城市、人数、月份和交通偏好，返回 `summary`、`source_ids`、`unresolved`。主智能体不接收交通专家完整聊天。

另用本地 Python 对合成价格数组计算总额，而不是让模型读取数千行原始价格：

```python
prices = [80, 90, 100]
bounded_result = {"count": len(prices), "min_usd": min(prices), "max_usd": max(prices)}
assert set(bounded_result) == {"count", "min_usd", "max_usd"}
print(bounded_result)
```

此片段说明有界结果的形状，不声称当前 Python 进程是安全沙箱。真正运行不可信代码前必须配置执行隔离、资源限额与禁用凭据，不能把普通 notebook 内核称为沙箱。

## 排障与验收

| 现象 | 排查与恢复 |
| --- | --- |
| 日期仍为四月 | 确认第五轮在同一 `session` 执行；检查摘要修订，丢弃过期候选 |
| 便签不存在 | 原 notebook 根本不写盘；确认执行了扩展写入单元格及自己的工作目录 |
| 重跑提示文件已存在 | 先核对自己文件，再决定更新；保护机制不是环境故障 |
| 摘要没有被调用 | 工具是否注册、智能体是否重建、请求是否明确；不要从最终文字猜调用 |
| 输入用量未下降 | 是否还发了完整历史、重复摘要或巨大工具模式；看实际使用量而非回答长度 |
| 新会话不知道计划 | 检查是否显式传入 `summary_text`；创建新会话不会自动读磁盘 |
| 401/403/429 | 按环境准备核对身份、部署、角色和预算；停止重复运行，避免额外费用 |

合格作业包括原六轮状态核对表、摘要函数能力边界说明、便签字段与修订证据、新会话输入组成和一条去敏检查记录。另列出未实现项：自动 token 阈值触发、权限隔离存储、并发写、加密、生命周期清理与生产沙箱。

## 演练状态与清理

当前为**待演练**；作者仅进行了固定源码的本地审阅，没有运行云模型、测得 token 降幅或完成平台正式验证。演练时记录实际日期、OS、Python/SDK 版本、模型、单元格、结果和失败原因。

清理会删除便签中的状态，无法从已结束会话自动恢复。确认不再需要且文件由本次实验创建后，在源码根先预览再删除：

```powershell
Get-Item .\lab-work\12\trip-state.json
Remove-Item .\lab-work\12\trip-state.json -WhatIf
```

核对预览后才移除 `-WhatIf` 执行。不要删除源仓库的 `vacation_agent_scratchpad.md`。关闭内核、去除输出中的真实数据；如资源端产生了实验智能体或会话，按管理员批准的清单清理，不删除共享模型。
