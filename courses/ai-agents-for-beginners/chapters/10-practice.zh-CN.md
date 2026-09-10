# 实作旅行评估与合成收据报销流程

## 学习目标与准备

本章包含两条独立路线：主 notebook 为旅行助手增加耗时观察和模型评估；报销变体把本地合成收据作为图像输入，经 OCRAgent 与 EmailAgent 生成报销邮件草稿。完成后，应能区分计时、trace、评估与真实业务操作，并核验金额和输出完整性。

先完成[环境准备](00-setup.zh-CN.md)和[可观测性概念](10-concepts.zh-CN.md)。使用 Windows PowerShell 7、Python 3.12+、`agent-framework-core==1.10.0`，两个 notebook 均使用 `FoundryChatClient` 与 `DefaultAzureCredential`。

需要 `AZURE_AI_PROJECT_ENDPOINT`、`AZURE_AI_MODEL_DEPLOYMENT_NAME` 和开发项目数据权限。报销图像分支还需要支持原生图像输入的已部署模型；不要默认所有文本部署都支持视觉。

固定源码：

- [10-python-agent-framework.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/10-ai-agents-production/code_samples/10-python-agent-framework.ipynb)。
- [10-expense_claim-demo.ipynb](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/10-ai-agents-production/code_samples/10-expense_claim-demo.ipynb)。

单元格索引从 JSON `cells[0]` 起，包含 Markdown。不要使用 Run All，报销原格会读取原始 `receipt.jpg`；本课程不读取、复制或上传该收据。

## 步骤一：建立主线环境并审查工具

**费用提示：旅行回答、评估和图像分析都调用收费模型；工具交互可能产生多轮请求。先确认预算、配额和实验身份，不使用生产资源或真实旅客资料。**

从源码根执行：

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('agent-framework-core'))"
Test-Path .\10-ai-agents-production\code_samples\10-python-agent-framework.ipynb
```

预期源码 SHA 正确、版本 `1.10.0`、文件存在。打开主 notebook，选 `.venv` 内核。**跳过索引 2 的 `%pip install ... -U`**，避免覆盖课程兼容版本。

运行索引 3、4 的配置与客户端。索引 7 定义 `get_flight_info`、`get_activity_suggestions`，只查询本地字典，包含 Paris、Tokyo、Barcelona，无真实预订。记录 Paris 的字典条目作为本次评估真值，不把它当作实时航班。

## 步骤二：运行旅行助手并观察耗时

索引 8 创建 `TravelAgent`，源码计时如下：

```python
start_time = time.time()
response = await agent.run(
    "I want to plan a day trip in Paris. What flights and activities do you recommend?",
)
elapsed = time.time() - start_time
print(f"Response ({elapsed:.2f}s):\n{response}")
```

确认预算后运行一次，记录本次实际 `elapsed`，不填写预设秒数。合格结果至少回应航班和活动两部分，与工具数据一致，并明确其建议属性。日期、出发地未给定，不能把一日游叙述当作已核验行程。

计时覆盖这次 `agent.run`，不含后续评估，也不能拆解每次模型和工具耗时。`time.time()` 是墙钟时间，可能受系统调时影响；若未来需要更可靠的持续时间测量，可在学习副本比较单调计时器，但不要把这个简单例子称为完整性能监控。

## 步骤三：运行评估者并核对依据

索引 10 创建无工具的 `ResponseEvaluator`，要求完整性、准确性、帮助性及总体分数，范围 1–5。执行：

```python
evaluation = await evaluator.run(f"Evaluate this travel agent response:\n\n{response}")
print(f"Evaluation:\n{evaluation}")
```

这又是一次收费请求。评分者只收到回答文本和量表，没有自动取得原始用户请求或工具真值；“准确性”更接近内部一致性审查，不是事实查证。

验收时人工比较以下项目：

- 是否同时覆盖航班与活动；
- 航班价格、时间是否来自本次工具字典，而非模型新增；
- 建议是否具体且承认缺失信息；
- 评估输出是否给齐四项分数和简短理由；
- 有无“评估者高分，但人工发现事实不符”的分歧。

新增课堂练习可在副本构造更完整的评估提示，显式附上原问题和合成真值，再仅重评一次。标明这是新增对照，不要宣称原 notebook 已有数据集评估、自动门禁或 token 统计。

## 步骤四：理解埋点而不连接外部遥测

主 notebook 只有手工计时；报销 notebook 也没有 Langfuse、OpenTelemetry exporter 或自动评估配置。原文的这些内容属于扩展设计，不能报告“已生成线上 trace”。

若已安装依赖允许，可以在学习单元格运行只围绕本地逻辑的示意：

```python
from agent_framework.observability import get_tracer

tracer = get_tracer()
with tracer.start_as_current_span("synthetic_local_check"):
    expected_parts = {"flights", "activities"}
    assert len(expected_parts) == 2
```

不要配置外部 exporter、真实用户标识或完整提示采集。本格没有调用模型；也不保证默认 tracer 会导出任何数据。预期只是不发生本地异常，不能用它作为遥测后端通过证明。

## 步骤五：报销变体先验证解析规则

打开报销 notebook 的学习副本，新内核。运行 `Import required libraries` 的索引 2 和客户端索引 3，再运行 `Define Expense Models` 的索引 5。

`Expense` 字段为 `date`、`description`、`amount`、`category`；`ExpenseFormatter.parse_expenses` 接收分号分隔条目，每项四列，以竖线分隔。先用合成数据做完全本地检查：

```python
synthetic_data = (
    "01-Sep-2026|Train ticket|20.00|Transportation;"
    "01-Sep-2026|Lunch|15.50|Meals"
)
expenses = ExpenseFormatter(raw_query=synthetic_data).parse_expenses()
assert len(expenses) == 2
assert abs(sum(e.amount for e in expenses) - 35.50) < 0.001
assert {e.category for e in expenses} == {"Transportation", "Meals"}

invalid = ExpenseFormatter(
    raw_query="bad segment;01-Sep-2026|Lunch|not-a-number|Meals"
).parse_expenses()
assert invalid == []
```

这验证当前解析行为：列数不等于四会被忽略，金额转换失败会打印错误并跳过。**部分条目错误时仍可能生成部分报销，不是严格全有或全无校验。** 日期和分类是字符串，负金额、无效日期、任意分类没有业务校验；金融精度通常还需要 `Decimal`、币种和明确舍入规则。

运行索引 7 定义 `generate_expense_email`。它的 `@tool(approval_mode="never_require")` 是因为只生成字符串，不连接邮箱。它合计解析成功项，并写出“附件已附”的模板句，但代码没有附加文件。结果只能叫草稿，不能叫“已发送报销申请”。

## 步骤六：创建可公开的合成收据

**隐私与写入提示：下一步会在本机写一个新的 JPEG；随后图像分支会把图像字节上传到模型服务。只能用本节生成的合成图，不得使用源码 `receipt.jpg`、真实发票、姓名、卡号、地址或个人签名。**

在报销学习 notebook 新增单元格，确认当前目录是自己可写的实验目录。下面文件名不含日期随机碰撞保护，所以先检查存在，绝不覆盖已有文件：

```python
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

synthetic_path = Path("synthetic-receipt.jpg")
if synthetic_path.exists():
    raise FileExistsError("Choose a new filename; do not overwrite an existing file.")

image = Image.new("RGB", (1100, 600), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.load_default(size=30)
draw.multiline_text(
    (40, 40),
    "SYNTHETIC TRAINING RECEIPT - NOT VALID\n"
    "Date: 01-Sep-2026\n"
    "Train ticket       USD 20.00\n"
    "Lunch              USD 15.50\n"
    "TOTAL              USD 35.50\n"
    "No personal or payment information",
    fill="black", font=font, spacing=20,
)
image.save(synthetic_path, format="JPEG")
assert synthetic_path.is_file()
```

若当前 Pillow 不支持 `load_default(size=30)`，使用系统已有的可读字体或由本地编辑器生成同样合成内容并保存真正 JPEG；不要升级整套课程依赖试错，也不要把 PNG 仅改后缀充当 JPEG。课堂记录图像是自行合成，不把它追加到课程发布资产。

## 步骤七：把合成图像交给 OCR 与邮件流水线

运行索引 9，定义 `load_receipt_image`：

```python
def load_receipt_image(image_path: str = "receipt.jpg") -> Content:
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    return Content.from_data(image_bytes, "image/jpeg")
```

默认参数仍指原收据，但我们始终显式传入 `synthetic_path`，不调用默认参数。运行索引 11，创建 `OCRAgent` 与 `EmailAgent`：

- OCRAgent 将日期转为 `dd-MMM-yyyy`，提取项目名、数字金额及分类，输出四列分隔文本，避免重复提取总计和小计。
- EmailAgent 将该字符串交给 `generate_expense_email` 生成草稿。

索引 14 同时建图和运行，**不要直接执行原格**。在副本将 `prompt` 与图像参数都改成合成场景，保留源码 API：

```python
workflow = WorkflowBuilder(start_executor=ocr_agent) \
    .add_edge(ocr_agent, email_agent) \
    .build()

receipt_message = Message(
    role="user",
    contents=[
        "Analyze this synthetic training receipt, extract itemized expenses, "
        "and generate an expense claim email draft. Do not count TOTAL as an item.",
        load_receipt_image(str(synthetic_path)),
    ],
)
events = workflow.run(receipt_message, stream=True)
async for event in events:
    if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
        print(event.data.text, end="", flush=True)
```

`Content.from_data` 将字节作为原生多模态图像传入，不是把文件路径当作模型能访问的本地文件，也不是把 base64 字符串塞进普通文本。执行前再次确认模型支持图像及预算获批。

验收应逐项对照合成真值：两条明细、20.00 与 15.50、合计 35.50、没有把 TOTAL 再当一项、无虚构旅客信息。若输出不包含中间 OCR 原文，不能仅凭最终总额断言提取完整；可在学习副本给工具入口添加去敏合成 `expense_data` 记录，复核原始四列文本。

日期、分类错误、漏项或重复项都应记为失败，不能因为邮件语气专业就通过。源码顶部提到饼图，但实际代码没有绘图工具或饼图生成；本分支也没有邮件发送、附件处理、费用政策审批和独立评估器。

## 步骤八：把观测转成最小评估集

不额外运行批量云测试，先给每条路线写三项检查：

| 用例 | 可直接验证的规则 | 人工判断 |
| --- | --- | --- |
| 旅行正常请求 | 航班与活动均出现且与工具字典一致 | 一日游建议是否合理地注明假设 |
| 报销合成正常收据 | 两条项目、合计 35.50、没有重复 TOTAL | 分类与说明是否清楚 |
| 报销错误格式 | 无效项被识别，不能把部分解析当完整成功 | 是否向操作者解释缺失、需要复核 |

记录运行入口、模型部署实际版本、真实耗时、错误和通过项。主线没有提供自动 cost 数据，不能推算出“已节省百分之多少”。缓存、模型路由、token 预算和批处理是后续设计，需要同一评估集证明没有质量回退。

## 故障定位与恢复

| 现象 | 排查与恢复 |
| --- | --- |
| 核心包或导入不兼容 | 确认 `.venv` 与 `1.10.0`，跳过 notebook `-U` 格；按准备章恢复隔离环境 |
| 看不到 trace 仪表盘 | 本例未配置 exporter；不要凭 `get_tracer` 或计时输出宣称已上传，课堂无需新建遥测平台 |
| 找不到收据 | 检查 `synthetic_path` 与内核工作目录；显式传参，不能回退读取真实 `receipt.jpg` |
| 不支持图像或 400 | 检查实际部署视觉能力、JPEG 真实格式和 `Content.from_data`；没有视觉部署时停在本地解析分支 |
| 合计不对 | 先数明细并核对 OCR，再查 `parse_expenses` 是否忽略错误行，最后检查是否重复总计；不让模型猜补金额 |
| 邮件说附件已附 | 模板句不代表附件真实存在；保持草稿状态，提交前需人工核验和另行实现附件 |
| 解析输出含错误敏感文本 | 停止使用真实数据，清除本轮输出并按组织要求处理暴露；课堂只接受合成输入 |
| 401/403/429 | 核对实际身份、项目权限、模型能力与配额；停止并发重试，按服务退避提示恢复 |

## 清理与验收状态

**删除前先核对对象归属并保留必要去敏证据；不可用通配符删除全部 JPG 或共享智能体。** 在同一内核查看 `synthetic_path.name`，确认是本节新建合成文件后：

```python
synthetic_path.unlink(missing_ok=True)
```

只清理自己的合成文件和学习副本输出，不碰源码 `receipt.jpg`。关闭内核，确认没有后台运行。若模型服务保留本次会话、图像输入或实验智能体，按项目政策和本次对象标识由资源所有者处理；删本地图不等于删云端数据。未启用外部遥测就没有该类平台资源需要删除。

本次预期交付学习记录包括旅行计时与评估对照、报销本地解析检查、合成收据核对表及未执行分支。没有真实发信或财务系统写入，也无需撤回报销。

**教学演练状态：待演练。** 本次编写未调用云端、上传收据、导出遥测、部署服务或测试生产；视觉分支、模型评分和正式课程平台验证仍由接收方演练。
