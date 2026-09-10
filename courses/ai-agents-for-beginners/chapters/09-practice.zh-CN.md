# 实作航班回退与独立响应评估

## 目标、源码与资源准备

本章让 `FlightBookingAgent` 尝试主航班工具，失败后转向备用工具，再由 `ResponseEvaluator` 评价答案。你还将修正学习副本中的问题—答案配对错误，避免评估错误对象。

先阅读[元认知概念](09-concepts.zh-CN.md)和[环境准备](00-setup.zh-CN.md)。环境为 Windows PowerShell 7、Python 3.12+，固定 `agent-framework-core==1.10.0`。源码：[09-python-agent-framework.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/09-metacognition/code_samples/09-python-agent-framework.ipynb)；本地为 `09-metacognition\code_samples\09-python-agent-framework.ipynb`。

主线实际使用 `FoundryChatClient` 与 `DefaultAzureCredential`，需要 `AZURE_AI_PROJECT_ENDPOINT`、`AZURE_AI_MODEL_DEPLOYMENT_NAME` 和开发项目数据权限，不是原文旧 Azure OpenAI HTTP 请求，也没有真实航空公司接口。单元格索引从 0 开始，包含 Markdown。

**费用与隐私提示：模型回答、工具选择和评估都会计费，回退可能增加模型往返。只使用虚构问题和获批开发部署，不填真实旅客身份或预订信息。代码中的航班与票价是固定示例，不可用于购票。**

## 步骤一：检查版本与内核

从源码根执行：

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
Test-Path .\09-metacognition\code_samples\09-python-agent-framework.ipynb
```

预期固定 SHA 一致、核心包 `1.10.0`、文件存在。选择 `.venv` 内核，跳过索引 2 的 `%pip install agent-framework ...`。执行索引 3 的导入与缺失变量检查、索引 4 的客户端初始化，不打印配置值。

## 步骤二：读主备数据，建立离线真值

在 `Primary and Backup Tools` 下，索引 7 定义：

- `get_flight_times(destination)`：主数据包含 Paris、Tokyo、Barcelona；未知城市抛出 `Exception("404: ...")`。
- `get_flight_times_backup(destination)`：备用数据包含 Berlin、Sydney、New York City；未知城市返回友好文本，不抛异常。

这是本地模拟的 404 字符串，不是一次真正 HTTP 响应。工具使用 `@tool(approval_mode="never_require")`，在此只读示例合理，但不能照搬到真实订票或付款。

先不调用模型，在自己的学习记录建立真值表：

| 输入 | 主工具 | 备用工具 | 合格回答约束 |
| --- | --- | --- | --- |
| Paris | 有资料 | 没有专属资料 | 不应无故声称主服务故障 |
| Berlin | 抛模拟 404 | 有资料 | 承认主工具失败，使用备用信息 |
| Atlantis | 抛模拟 404 | 返回无资料 | 说明两处均无资料，不编造航班 |
| paris | 大小写不匹配 | 大小写不匹配 | 识别严格字符串匹配问题，而非推断真实城市没航班 |

如果需要无云验证，可以在单独学习单元格复制源码两个函数，暂不复制 `@tool` 装饰器，作为普通 Python 函数执行；不要猜测装饰后对象的同步调用方式：

```python
assert "08:00" in get_flight_times("Paris")
try:
    get_flight_times("Berlin")
except Exception as exc:
    assert "404:" in str(exc)
else:
    raise AssertionError("Expected the primary lookup to fail")
assert "09:00" in get_flight_times_backup("Berlin")
assert "No flights found" in get_flight_times_backup("Atlantis")
```

上面仅用于“已复制无装饰器函数”的离线单元格，不能直接覆盖主 notebook 内已注册的工具对象。完成后重启主 notebook 内核并按准备顺序恢复，防止把本地夹具混入云端实验。

## 步骤三：保留每个问题的独立响应

索引 9 的 `Self-Reflecting Agent with Error Recovery` 创建 `FlightBookingAgent`，要求先主系统、失败后备用、透明解释、最后简短自评。

**运行前先在学习副本修正变量保存方式。** 原格先问 Paris，把结果放在 `response`；后问 Berlin，又覆盖 `response`。索引 11 的评估提示却仍写 Paris。若照原顺序执行，会让评估者评价“巴黎问题 + 柏林答案”。

在学习副本使用清晰名称替代索引 9 的两个运行部分：

```python
paris_question = "What flights are available to Paris?"
paris_response = await agent.run(paris_question)
print(paris_response)

berlin_question = "What flights are available to Berlin?"
berlin_response = await agent.run(berlin_question)
print(berlin_response)
```

这两次运行会调用收费模型；每次完成后立即检查，不使用 Run All。

验证 Paris：内容与主字典一致，不无故加上未在工具中的航班时间；可以补充解释，但不能声称真实票价已确认。验证 Berlin：答案应体现主来源无法找到、转向备用，并使用备用信息。

仅从自然语言“我用了备用工具”不能证明真的回退。可在学习副本的两个工具函数体入口向一个本地 `tool_calls` 列表追加函数名和虚构目的地，在每个请求前清空列表；核对 Berlin 顺序为主后备。输出记录只存本次合成参数，不保存真实用户资料。

## 步骤四：测试双方都无数据与停止条件

在预算允许时新增一次请求：

```python
missing_question = "What flights are available to Atlantis?"
missing_response = await agent.run(missing_question)
print(missing_response)
```

合格行为是说明无法找到航班、提供合理下一步，不应把无资料当工具成功预订。源码没有显式设置最大工具回退次数；首次实验如果观察到重复查询，不等待其无限循环，应停止内核执行并记录问题，由应用控制层加入调用预算后再演练。

“重新调用一个相同主工具”不会产生新信息。备用来源也无数据时，修订策略可能是请求其他目的地，而不是编造结果。不要扩展成真实航空接口或购买动作。

## 步骤五：正确配对地进行独立评估

执行索引 11 中 `evaluation_agent = client.as_agent(...)` 的定义，它同样配有两个工具，按完整性、准确性、帮助性各评 1–5，并给一条建议。

不要运行原有混淆变量的 `eval_prompt`。在学习副本使用：

```python
eval_prompt = f"""Question: {berlin_question}
Agent Response: {berlin_response}

Please evaluate the above response."""
evaluation = await evaluation_agent.run(eval_prompt)
print(evaluation)
```

确认评估对象就是刚才的 Berlin 答案；另评 Paris 时同时替换问题与响应。新增评估会产生模型费用，评估者调用工具还可能进一步增加往返。

验收不是“整体分数高”，而是：

1. 三个维度都有 1–5 范围内分数和理由。
2. 准确性依据与工具字典一致，而非只称文字流畅。
3. 指出或正确认可回退说明。
4. 不将“模拟资料”判定为实时航班保证。
5. 建议具体且能转化为下一次测试。

这里的评分输出是自由文本，没有 `response_format`，不能假设它是严格 JSON 或机器可执行放行条件。评估者与被评估者可能共享模型偏差，必须保留离线真值与人工核对。

## 步骤六：把一次反馈转成策略改进

选择一个确实观察到的问题，在副本仅改一处指令，然后重跑受影响的最小案例。例如：

- 如果未说明回退来源，强调只在真的调用备用工具后报告备用结果。
- 如果编造票价，要求只能引用工具数据，并明确非实时报价。
- 如果大小写导致失败，先设计确定性的城市规范化方案，而不是无限让模型猜字符串。

记录修改前后的问题、工具调用、答案和评估，不给没有运行的数据打分。这个步骤是受控改进，不是自动学习或完整 Corrective RAG；本 notebook 没有向量库、搜索服务、代码生成器或持久记忆。

若想与原文更广的元认知主题对照，画出“当前主备回退”与“纠正性 RAG 重写查询再检索”的区别，并写出哪一处需要新增可信检索工具。不要直接执行原文的 `exec(code)` 或字符串拼接 SQL。

## 常见问题与恢复

| 现象 | 排查与恢复 |
| --- | --- |
| 出现 404 文本 | 先区分源码刻意抛出的工具异常与真正服务端 404；Paris 等存在城市才应主工具成功 |
| 异常直接终止而没回退 | 检查选用内核、工具异常是否被当前框架交还模型；保留去敏异常，不声称回退已实现；先用离线函数测试定位 |
| 评估说答案答非所问 | 先检查是否仍在使用覆盖后的 `response`，再检查模型质量；纠正问题—答案配对后再付费重跑 |
| Berlin 未尝试主工具 | 对照真实工具调用记录与指令；缺少记录就写“无法证实”，不要凭最终文本推断 |
| 莫名出现另一座城市 | 检查工具参数、上次内核状态、提示；每次实验使用独立问题和具名响应 |
| 评估高分但事实不符 | 用离线字典判定事实失败；完善评估准则和真值，而不是信任自评分 |
| 401/403/429 | 按准备章核对凭据、项目权限和配额；停止连续重试，保护预算 |

## 清理、预期产物与演练记录

预期产物包括：主备真值表、Paris/Berlin/无资料三类检查、正确配对的评估记录，以及一次有证据的策略改进说明。未运行的分支写“未执行”，没有高分或固定耗时保证。

清理前保留必要的去敏证据，再清除 notebook 输出和自己创建的 `tool_calls` 记录，关闭内核。主备工具没有创建预订、文件或数据库，无真实订单需要取消。Foundry 如保留实验智能体或会话，由资源所有者核对本轮对象后清理，不能批量删除共享模型。

**教学演练状态：待演练。** 本次交付没有调用模型、评估真实旅客数据或验证服务端回退；代码问题已在学习步骤中明确，源 notebook 未被改动。
