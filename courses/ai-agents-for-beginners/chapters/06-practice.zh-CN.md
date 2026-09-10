# 实作元提示、风险分级与行动前审批

## 目标、环境与源码

完成本章后，你应能生成一份候选系统消息，验证三级门禁与拒绝修订循环，读懂 JSONL 决策记录，并指出示例没有实现的真实执行和人工升级环节。先阅读[信任边界概念](06-concepts.zh-CN.md)和[环境准备](00-setup.zh-CN.md)。

工作环境为 Windows PowerShell 7、Python 3.12+，从固定提交的源码仓库根启动 VS Code，并选择 `.venv` 内核。保留课程 `agent-framework-core==1.10.0`；本模块实际用 `openai.OpenAI`，无需为它另装或升级 MAF。

完整入口：

- [06-system-message-framework.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/06-building-trustworthy-agents/code_samples/06-system-message-framework.ipynb)：4 个代码单元格，无 Markdown 步骤标题。
- [06-human-in-the-loop.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/06-building-trustworthy-agents/code_samples/06-human-in-the-loop.ipynb)：`Pattern 1: Pre-action gate`、`Pattern 2: Risk tiering`、`Pattern 3: Audit log and revision loop`。

本章提到的“单元格索引”按 notebook JSON 的 `cells` 数组从 0 计数，包含 Markdown，不是执行编号。实验修改放在学习副本或新增单元格，不覆盖固定源码。

## 步骤一：确认直接 Azure OpenAI 路线

**费用与权限提示：下文 `client.responses.create` 会调用收费模型；即使 `DEMO_MODE=True`，提案生成仍然联网计费。** 只使用资源所有者批准的开发部署和虚构业务数据，不使用生产客户信息。需要支持 Responses API 的 Azure OpenAI 部署及相应 Entra 数据访问权限。

准备 `AZURE_OPENAI_ENDPOINT` 和 `AZURE_OPENAI_DEPLOYMENT`，分别来自 Azure OpenAI 资源端点和已部署模型名称。这里不能用 `AZURE_AI_PROJECT_ENDPOINT` 代替。身份使用 `DefaultAzureCredential` 配合 `get_bearer_token_provider`；它可能选择其他已配置身份，不保证总是 CLI。

在源码根做只读检查：

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; load_dotenv(); names=['AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_DEPLOYMENT']; print({n: bool(os.getenv(n)) and '<' not in os.getenv(n,'') for n in names})"
```

预期 SHA 为 `25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595`，两个布尔值均为真。不要打印端点、凭据、环境文件或令牌。身份登录步骤沿用准备章；此检查不能证明服务权限。

## 步骤二：生成并人工审核系统消息

打开 `06-building-trustworthy-agents\code_samples\06-system-message-framework.ipynb`。

1. 运行索引 0：导入、加载配置并读取直接 OpenAI 变量。
2. 运行索引 1：建立 Entra token provider 和 `OpenAI` 客户端。实际端点拼接为 `f"{endpoint.rstrip('/')}/openai/v1/"`，无需添加旧式 `api-version`。
3. 索引 2 定义 `role = "travel agent"`、`company = "contoso travel"`、`responsibility = "booking flights"`。先保留它们，便于对照。
4. 确认预算后只运行一次索引 3。关键调用如下，完整元提示在源码中：

```python
response = client.responses.create(
    model=deployment,
    input=[
        {"role": "system", "content": "You are an expert at creating AI agent assistants."},
        {"role": "user", "content": f"You are {role} at {company} that is responsible for {responsibility}."},
    ],
    temperature=1.0,
    max_output_tokens=1000,
    top_p=1.0,
    store=False,
)
print(response.output_text)
```

上面是缩短元提示后的学习摘录，实际基线运行保留 notebook 的完整提示。`store=False` 不等于不存在任何服务日志，也不免除数据处理责任。

验证：`response.output_text` 非空；包含角色与航班职责；没有把候选提示当作已经完成预订的结果。人工指出至少一项遗漏，例如没有规定取消前审批。仅在副本里扩展 `responsibility` 加入“预订和取消前提出可审核提案”，再次运行，比较两个候选版本。模型不一定使用同样栏目或措辞，不能用字符串完全相同作为验收条件。

## 步骤三：先在本机检查门禁逻辑

打开第二个 notebook。索引 1 创建 `GATE_LOG_PATH`，文件名形如 `gate_log_时间戳.jsonl`，按当前内核工作目录保存；这个单元格要求配置存在，但没有调用 `responses.create`。运行索引 3 和 5，分别定义 `gate_action`、`classify_risk`、`tiered_gate`。

在新单元格运行以下本地检查，不发模型请求、不写文件：

```python
assert classify_risk("look up flights") == "low"
assert classify_risk("schedule a reminder") == "medium"
assert classify_risk("send an email") == "high"
assert classify_risk("unrecognized operation") == "medium"
assert classify_risk("search and delete records") == "high"
assert tiered_gate("schedule a reminder")["decision"] == "approve"
assert gate_action("send an email", "high", attempt=0)["decision"] == "deny"
assert gate_action("send an email", "high", attempt=1)["decision"] == "approve"
```

最后两项只适用于 `DEMO_MODE=True`，验证的是脚本化“第一次拒绝、重试批准”。没有断言失败才表示代码满足这些具体规则，不代表策略安全。特别注意：英文子串 `get`、`read` 等可能误匹配其他词，中风险也没有真正的批量审核系统。

在学习副本设 `DEMO_MODE=False`，单独调用一次 `gate_action("send a test draft", "high")`，输入 `deny`；再调用并直接回车，验证仍为拒绝。不要把批准测试接到真实发信工具。无交互终端可能触发 `EOFError`，代码应安全拒绝。测试完恢复 `DEMO_MODE=True`，避免后续练习等待输入。

## 步骤四：记录决策并理解修订上限

**本步骤将产生本地日志，日志含完整动作文字与拒绝理由。只使用虚构目标；写入前确认工作目录可写且没有共享客户数据。**

运行索引 7，定义 `log_decision`、`propose_action`、`run_with_revision`。先不要运行索引 8。

关键链路是：

```python
action = propose_action(goal, prior_rejection=prior_reason)
decision = tiered_gate(action, attempt=attempt)
decision["attempt"] = attempt
log_decision(decision)
```

`run_with_revision(goal, max_revisions=1)` 最多产生两次提案，不是一次；批准就返回，否则把理由传回模型。达到上限时返回 `final="max_revisions_reached"`。`escalate` 没有专门停止或工单分支，实际仍进入下一轮，因此不能把这个词当作已通知人工。

无云资源时也可验证有限循环：在新增单元格暂存原 `propose_action`，用本地函数替代，最后恢复：

```python
original_propose_action = propose_action
seen_reasons = []
def scripted_proposal(goal, prior_rejection=None):
    seen_reasons.append(prior_rejection)
    return "send an email"
try:
    propose_action = scripted_proposal
    decision = run_with_revision("synthetic approval exercise", max_revisions=1)
    assert decision["decision"] == "approve"
    assert len(seen_reasons) == 2
    assert seen_reasons[0] is None and seen_reasons[1]
finally:
    propose_action = original_propose_action
```

这仍会写本地 JSONL，但不调用模型；它是新增的演练夹具，不是源码内置离线模式。执行前必须已定义相应函数与 `GATE_LOG_PATH`，并保持 `DEMO_MODE=True`。若没有 Azure 配置，可以在独立学习 notebook 仅复制索引 3、5、7 的函数定义，并先导入 `json`、`datetime`、`timezone`、`Path`、设置 `DEMO_MODE=True` 及自己的唯一日志路径；不要复制或执行云客户端初始化。

## 步骤五：有预算时运行三类目标

恢复原 `propose_action`，在已获批准的实验资源中运行索引 8。三个目标分别是查询 Seattle 天气、安排值机提醒、发送营销邮件。它们是交给模型的提案目标，不是真的天气工具、日历或邮件发送。

每个目标 `max_revisions=1`，整个单元格理论上最多产生六次提案模型请求；生成语句会影响风险分类，所以不要预先断言恰有几条日志或所有目标都成功。核对：

- 每次尝试有 `ts`、`action`、`risk_tier`、`decision`、`reason`、`attempt`。
- 同一目标的尝试次数不超过两次；拒绝理由确实传给下一次提案。
- 终端“approve”只表示门禁返回批准，不能写作“邮件发送成功”。
- 日志记录数等于实际做出的门禁决策数，而不是用户目标数。

仅检查本次日志格式，不输出全文：

```python
records = [json.loads(line) for line in GATE_LOG_PATH.read_text(encoding="utf-8").splitlines()]
required = {"ts", "action", "risk_tier", "decision", "reason", "attempt"}
assert records and all(required <= r.keys() for r in records)
assert all(r["decision"] in {"approve", "deny", "escalate"} for r in records)
```

同一秒重新初始化可能得到相同文件名；不要依赖秒级时间戳实现强唯一性。保留本轮路径，不重新执行初始化后误读另一轮日志。

## 故障定位与恢复

| 现象 | 按顺序处理 |
| --- | --- |
| 缺少 `AZURE_OPENAI_ENDPOINT` | 检查变量名和内核工作目录；用准备章方法只检查是否存在；不要把 Foundry 项目端点换名塞入 |
| 401/403 | 核对 `DefaultAzureCredential` 实际选择的身份、租户和 Azure OpenAI 数据角色；不扩大为订阅管理员 |
| 不支持 `temperature`、`top_p` 或 API | 确认部署实际模型和 Responses 支持范围；在副本去掉明确不支持的可选参数，并记录差异，不升级 SDK 猜测 |
| 高风险重试自动批准 | 这是演示分支；真实审批需 `DEMO_MODE=False`，并实现真正的执行层和升级停止语义 |
| 分类结果意外 | 检查子串匹配顺序：high、low、medium；未知默认 medium。不要把语义误判解释为模型正确降险 |
| 日志无法写入或 JSON 损坏 | 停止循环；核对当前目录、文件权限和并发写入；保留损坏副本供排查，使用新的自己拥有的日志路径 |
| 429、超时 | 停止批量重跑，按服务退避要求等待并降低调用数；提案失败不应被当作已批准 |

## 清理与验收记录

确认无需保留且仅属于自己的演示日志后再删除；删除是不可逆操作，不能使用会匹配其他人的 `gate_log_*.jsonl` 批量命令。可在保存 `GATE_LOG_PATH` 的同一内核里执行：

```python
print(GATE_LOG_PATH.name)
# 核对上方确为本轮演示文件后，单独执行下一行。
GATE_LOG_PATH.unlink(missing_ok=True)
client.close()
```

清除含动作详情的 notebook 输出，关闭内核。演示不执行真实预订、支付或发信，无这些业务资源需要撤销；直接 OpenAI 部署由资源所有者决定保留或删除。不要删除共享部署。

验收记录分别填写：离线断言、系统消息候选审查、真实提案调用、日志条数及拒绝修订证据。记录真实工具版本和实际错误，不填写虚构耗时。

**教学演练状态：待演练。** 本手册没有调用云端，也未验证真实审批平台或生产安全性；正式运行与平台导入验收由接收方完成。
