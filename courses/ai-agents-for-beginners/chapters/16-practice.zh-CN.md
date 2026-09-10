# 验证支持代理的路由、审批与发布关卡

## 学习目标

使用源 notebook 的真实规则完成一个无云依赖的控制面练习：测试路由边界、退款阈值、客户隔离和评估门槛。按资源条件再选择 Foundry 请求、Search、审批集成、可观测性和发布后 smoke test 扩展。

## 准备与执行前警告

阅读[环境准备](00-setup.zh-CN.md)与[生产部署概念](16-concepts.zh-CN.md)。Windows、PowerShell 7、Python 3.12+；所有命令从固定提交源码仓库根目录运行。只修改 `lab-work\16-support` 中的练习副本，不覆盖原 notebook、测试目录或工作流。

**费用与权限：** 步骤一至三无模型调用、不写订单或退款系统，仅创建练习脚本。云端扩展调用训练模型会计费；Search、日志、托管服务和 Actions 运行也可能有成本。接收方应预先规定请求预算和资源所有者。未经额外授权不部署、不修改生产工单、不退款、不创建仓库机密和联邦身份。

来源为[支持代理 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/16-deploying-scalable-agents/code_samples/16-python-agent-framework.ipynb)。编号按零基 `cells`，含 Markdown。

固定版本的[模块 README](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/16-deploying-scalable-agents/README.md)对应这一份 Python notebook，没有 .NET notebook。内存/Search 检索、大小模型和模拟发布是同一 notebook 的分支；独立的 hosted smoke test 来源及前提见步骤六，不把它误列为已经包含的部署实现。

## 步骤一：检查实际路径，不执行整个 notebook

```powershell
$nb = Get-Content .\16-deploying-scalable-agents\code_samples\16-python-agent-framework.ipynb -Raw | ConvertFrom-Json
foreach ($i in 5, 11, 16, 18) {
    "CELL $i"
    $nb.cells[$i].source -join ''
}
New-Item -ItemType Directory -Force -Path .\lab-work\16-support | Out-Null
```

预期能找到金额阈值 50、英文复杂性关键词、逐例 0.5/总计 0.8 的门槛，以及只打印提示的 `release`。单元格 3 会加载环境并创建 Foundry 客户端；14、16、18 会请求模型，因此主线不要执行。

## 步骤二：抽取纯函数并做离线断言

在 `lab-work\16-support\rules_check.py` 保存以下完整脚本。从已审阅的固定源单元格中只抽取白名单纯函数和字面量，不执行单元格顶层的客户端创建、环境加载或 `await`。这不是对任意未知 notebook 的安全执行器。

```python
import ast
import asyncio
import json
import re
from pathlib import Path
from types import SimpleNamespace

source = Path(
    r"16-deploying-scalable-agents\code_samples\16-python-agent-framework.ipynb"
)
nb = json.loads(source.read_text(encoding="utf-8"))
scope = {
    "re": re, "SMALL_MODEL": "small-demo", "LARGE_MODEL": "large-demo",
}
functions = {
    "refund_needs_approval", "_in_memory_search", "memory_context",
    "normalize", "is_simple", "choose_model", "score_response",
    "evaluation_gate",
}
constants = {
    "REFUND_APPROVAL_THRESHOLD", "KNOWLEDGE_BASE", "CUSTOMER_MEMORY",
    "COMPLEX_SIGNALS", "TEST_CASES",
}
for index in (5, 7, 9, 11, 16):
    tree = ast.parse("".join(nb["cells"][index]["source"]))
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in functions:
                assert not node.decorator_list
                selected.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in constants:
                    scope[target.id] = ast.literal_eval(node.value)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"),
         scope)

assert scope["refund_needs_approval"](50.0) is False
assert scope["refund_needs_approval"](50.01) is True
assert scope["choose_model"]("Where is order A1001?") == "small-demo"
assert scope["choose_model"]("Please refund order A1001") == "large-demo"
assert scope["choose_model"]("word " * 21) == "large-demo"
assert "30 days" in scope["_in_memory_search"]("returns")
assert "A1002" in scope["memory_context"]("cust-42")
assert "A1003" in scope["memory_context"]("cust-99")

query = "Where is my order?"
old_key_a = scope["normalize"](query)
old_key_b = scope["normalize"]("  WHERE is my order? ")
assert old_key_a == old_key_b
new_key_a = ("cust-42", "training-policy-v1", old_key_a)
new_key_b = ("cust-99", "training-policy-v1", old_key_b)
assert new_key_a != new_key_b
print("RULES PASS; source cache key collision demonstrated locally")

class FakeAgent:
    def __init__(self, fail_first=False):
        self.fail_first = fail_first
    async def run(self, query):
        case = next(c for c in scope["TEST_CASES"] if c["input"] == query)
        if self.fail_first and case is scope["TEST_CASES"][0]:
            return SimpleNamespace(text="unrelated")
        return SimpleNamespace(text=case["expected"][0])

async def check_gate():
    scope["support_agent"] = FakeAgent()
    assert await scope["evaluation_gate"](scope["TEST_CASES"], 0.8)
    scope["support_agent"] = FakeAgent(fail_first=True)
    assert not await scope["evaluation_gate"](scope["TEST_CASES"], 0.8)
    print("GATE PASS: 4/4 accepted, 3/4 blocked; no model called")

asyncio.run(check_gate())
```

执行：

```powershell
python .\lab-work\16-support\rules_check.py
```

通过标准：退出码为 0，路由断言全部通过；伪代理仅返回每例的一个关键词仍可使单例得分 50% 通过；4/4 可发布、3/4 被阻止。后者故意演示源评分器宽松，而不是证明问答正确。所有 `PASS` 是预期文本，实际结果由演练者记录。

## 步骤三：加入不能自动越过的模拟审批

在同目录新建练习文件，或在规则脚本末尾添加以下本地模拟。它不依赖 Agent Framework，也不声称实现了框架的批准/恢复协议。

```python
def simulate_refund(order_id, amount, approved=False):
    if type(amount) not in (int, float) or not (0 < amount <= 5000):
        return "REFUSED"
    proposal = (order_id, amount, "USD")
    if not approved:
        return ("PENDING", proposal)
    return ("SIMULATED", proposal)

assert simulate_refund("A1002", 128.50)[0] == "PENDING"
assert simulate_refund("A1002", 128.50, approved=True)[0] == "SIMULATED"
assert simulate_refund("A1002", -1) == "REFUSED"
assert simulate_refund("A1002", True) == "REFUSED"
print("APPROVAL PASS: no real refund performed")
```

演练者先读取精确提案，再在虚构案例中选择批准或拒绝。即使金额是 10，也先暂停，以对应源 `issue_refund` 的 `always_require`。若要实现“小于等于 50 自动、大于 50 人工”，必须另写政策分支并测试 50 与 50.01；不能认为源辅助函数已经替你接好了分支。

审批不应允许批准后悄悄更换订单号、金额或收款方。将此要求带到[签名授权实践](18-practice.zh-CN.md)验证；单纯布尔变量不是生产授权。

## 步骤四：可选 Foundry 客户端演练

只有接收方确认培训资源后才运行此节。沿用[根 requirements](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/requirements.txt)安装的环境，**跳过单元格 2 的无约束 `%pip install agent-framework ...`**，避免冲掉核心 `1.10.0` 约束。运行前 `python -m pip check`，记录实际集成包版本。

| 配置 | 用途与最低资源 |
| --- | --- |
| `AZURE_AI_PROJECT_ENDPOINT` | 接收方提供的 Foundry project endpoint |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | 已部署并授权调用的训练模型 |
| `AZURE_AI_SMALL_MODEL` / `AZURE_AI_LARGE_MODEL` | 可选的实际部署名；省略会回退到同一默认模型 |
| `az login` | 学习者培训身份；源码使用 `AzureCliCredential` |
| Search 配置 | 主线不需要；扩展节才需要 |

只设置已选择路线所需的最小配置；删除未使用的可选变量，不能将 `.env.example` 中的 `...` 原样留下。非空的 `AZURE_SEARCH_SERVICE_ENDPOINT` 与 `AZURE_SEARCH_API_KEY` 会使源代码选择 Search 分支；非空的 `AZURE_AI_SMALL_MODEL`/`AZURE_AI_LARGE_MODEL` 则会被当作实际部署名，连省略号也不例外。

在练习 notebook 副本中从单元格 3 逐项执行 5、7、9、11、13。对每一项先确认全局对象、工具是否仍为模拟实现。强制 `USE_AZURE_SEARCH = False` 使用内存政策库，避免机器上已有环境触发意外 Search 请求。

在复制的 `handle_support_request` 中，将缓存键改为如下教学形式，并规定只缓存已审核的公开 FAQ、绝不缓存退款/开单等写操作：

```python
key = (customer_id, "training-policy-v1", normalize(query))
```

这个键比原始键更好，但真实系统还应绑定授权范围、会话及知识库版本并设置 TTL。不要把此一行称为完整缓存治理。重启前确认缓存会丢失，验证这是内存演示而不是外置状态服务。

随后运行源单元格 14：退货窗口、A1002 查询、重复退货窗口。预期第三次命中缓存；前两次实际走什么模型取决于规则与部署配置。分别检查 `30 days`、A1002 的 `processing`，并确认引用的是工具事实。两个模型名相同时只算“规则演练”，不得声称测得大小模型成本差。

单元格 16 和 18 各调用一次四例评估；反复运行会重复计费。请求预算要把两轮都算进去。`support_agent` 使用 small tier，评估没有经过缓存/路由请求处理器；因此应另给请求处理器设计测试，不能用该门槛覆盖整条生产链。

## 步骤五：按需选择生产关注点变体

### Azure AI Search 检索

接收方应提供已有培训 Search 服务、仅查询权限凭据与包含可检索 `content` 字段的索引。设置 `AZURE_SEARCH_SERVICE_ENDPOINT`、`AZURE_SEARCH_API_KEY`，以及可选 `AZURE_SEARCH_INDEX_NAME`（默认 `contoso-policies`）。本 notebook 不创建索引、不上传四条政策。

先在授权查询环境中确认 `returns` 能返回 30 天政策，再在练习副本启用 `USE_AZURE_SEARCH`。通过条件：检索结果来自指定索引，缺失内容能明确返回无匹配；若配置了错误 endpoint，源代码不会自动降级回内存，须修正配置或显式退回主线。不要为排错授予索引管理密钥。

### 人工审批、并发与三档路由

框架扩展需要在练习副本中保留完整响应对象，展示工具调用请求、让人工查看精确参数、批准或拒绝后再按该版本框架的协议恢复。源码未给出完整恢复实现；没有经过此集成验收时，将“真实 HITL”标为未完成，不能把 `response.text` 或模拟退款消息算作批准证据。

并发扩展可用 `asyncio.Semaphore(2)` 包围每次未命中模型调用；数字是教学上限。用本地假请求验证同时在途数从不超过 2、排队请求可取消、超时有明确结果，然后才考虑少量云端请求。只读调用的有限指数退避与写工具的幂等/补偿分别设计。

三档路由变体可为 complaint/escalate 加一档 reasoning 部署。先用假部署名断言路由，再经费用批准接真实模型；各档都要独立过质量门槛。不要把升级档位当作审批替代品。

### 遥测和成本报告

先检查单元格 13 的 `tracer` 是否为 `_NoopTracer`。需要真实追踪时，由接收方配置该固定 Agent Framework 版本支持的 OpenTelemetry 导出与目标，不复制未经验证的连接字符串。

给练习请求附加匿名请求号、路由档位、缓存结果和状态，不记录客户姓名、完整提示、订单正文或秘密。通过条件是未命中请求可关联到模型/工具子 span，缓存命中也有事件证据；空 tracer 或仅看到本地 `print` 不算导出成功。

用十个预先写好的混合查询收集 small、large、cache 次数，并使三者总和等于 10；记录输入/输出 token（若服务提供）及计价来源，再计算估计值。未取得实际用量时只提交次数报告，费用写“未测”，不得填写虚构金额。

## 步骤六：独立的 Hosted Agent smoke test 变体

需要接收方**预先部署**能提供 Responses endpoint 的 `ContosoSupportAgent` 及它依赖的工具。本 notebook 没有托管运行时部署器，单元格 18 不能补齐这一前提。本交付阶段不触发工作流。

来源为[测试目录说明](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/tests/README.md)、[六项测试目录](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/tests/lesson-16-smoke-tests.json)与[工作流](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/.github/workflows/smoke-test.yml)。

1. 接收方在课程演练仓库配置 Azure OIDC 联邦关系，以及 `AZURE_CLIENT_ID`、`AZURE_TENANT_ID`、`AZURE_SUBSCRIPTION_ID`。这些配置经安全渠道处理，不写入交付文档。
2. 调用身份至少需要项目作用域 `Azure AI User`；源 workflow 使用 `id-token: write` 与 `contents: read`。当前第三方动作引用 `JFolberth/ai-smoketest@v1` 并非完整 SHA，正式供应链准入由接收方处理，不能把它说成已精确锁定。
3. Actions 中选择 `Smoke-test hosted agents`，`tests_file` 为 `tests/lesson-16-smoke-tests.json`，填培训 project endpoint 与匹配的 agent name。身份的服务 token audience 应为 `https://ai.azure.com/`。
4. runner 面向 `POST {project_endpoint}/agents/{agent_name}/endpoint/protocols/openai/responses`。六例中两轮上下文通过 `save_response_id_as: order_context` 和 `use_previous_response_id` 关联。
5. 通过标准是六个 case 全部满足 HTTP/文本断言，且第二轮保留 A1002 上下文。保存工作流运行标识、源码版本和脱敏断言结果。若 404，先确认确有 hosted endpoint，不重跑 notebook 冒充部署。

子串断言较弱，特别是离题题目；它们仅用于“端点可达且具备基本行为”的发布后检查，不替代安全评估和真实审批验证。

## 步骤七：完成订阅计费扩展作业

在练习副本将工具替换为 `get_subscription_status`、`get_invoice`、`issue_credit`，数据全部虚构。加入退款、账期和取消政策三篇短文；扩展到至少八个评估用例，其中至少两例必须走审批，另有拒绝分支。

提交十条混合查询的路由/缓存计数和规则理由。通过标准为：八例按预先声明门槛判定；两例批准前不能执行；被拒绝动作没有副作用；十条计数对齐；没有跨客户缓存混用。云资源不足时用假代理完成控制流，但明确模型质量和 hosted 行为未验证。

## 故障排查

| 现象 | 先查什么 |
| --- | --- |
| 纯函数脚本提取失败 | 是否使用固定提交和零基单元格，禁止改成执行所有单元格 |
| 包版本冲突 | 检查是否运行了原安装单元格，恢复根 requirements 的兼容约束 |
| 缓存返回其他客户上下文 | 停止多客户演练，清空练习缓存，隔离 key 后重测 |
| 审批请求没有文本 | 不丢弃完整响应；源样例不含恢复逻辑，标为集成未完成 |
| Search 报 403/404 | 查询权限、索引名称、`content` 字段；不要扩大到管理员权限 |
| smoke 403 或 404 | 区分项目作用域身份和真实托管 endpoint 前提 |
| 关卡总是通过 | 查看 0.5 弱关键词匹配；加入反例而非信任绿色提示 |

## 清理、预期结果与演练记录

重启练习 kernel 可清空 `TICKETS`、`CUSTOMER_MEMORY`、`response_cache` 和客户端对象；不是持久化数据清理证明。关闭本次创建的客户端/追踪导出器。由接收方清理独占的培训代理版本、日志或 Search 索引，**不要删除共享项目、共享模型或订阅资源**。

本地目录确认不含他人文件后先预览：

```powershell
Remove-Item -LiteralPath .\lab-work\16-support -Recurse -WhatIf
```

核实后才去掉 `-WhatIf`。预期交付包括纯函数断言、模拟审批正反例、缓存隔离说明、选择了哪些扩展及其阻塞项。

**演练状态：待演练。** 没有部署、实际模型质量、遥测导出或账单观测结论；接收方应填实际版本、日期、断言结果、云端调用数量与未完成项。下一章见[本地代理概念](17-concepts.zh-CN.md)。
