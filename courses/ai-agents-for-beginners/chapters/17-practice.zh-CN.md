# 在受限项目目录中构建本地工程助手

## 学习目标

先不启动模型，验证本地文件工具的正常路径和越界拒绝；再在接收方准备好的机器上连接 Foundry Local、建立本地 RAG、检查工具循环，并按需接入只读 MCP。最终交付的是可核查的工具证据，而不是对模型回答的主观评价。

## 准备、权限与资源警告

完成[环境准备](00-setup.zh-CN.md)和[本地代理概念](17-concepts.zh-CN.md)。本章针对 Windows、PowerShell 7、Python 3.12+；从固定版本仓库根目录开始，练习文件只放 `lab-work\17-local`。

**执行前警告：** 步骤一、二不联网、不用模型、仅写虚构文件。后续安装 Foundry Local、Qwen 和 Chroma 嵌入模型需要软件授权、网络和足够磁盘/内存，可能是较大下载；内容交付阶段不执行。先由接收方核实设备配置与缓存，不把下载时间或内存建议当作保证。不要索引真实客户数据、用户目录或秘密配置。

基础环境使用[固定源码 requirements](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/requirements.txt)，包含 `foundry-local-sdk`、`openai>=1.108.1`、`chromadb` 和 `mcp[cli]`。这些不是完整精确版本锁；记录最终包版本，保留 Agent Framework 核心 `1.10.0` 约束。主线标准库工具验证无需为此安装全部依赖。

## 步骤一：建立可删除的虚构项目

来源为[本地助手 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/17-creating-local-ai-agents/code_samples/17-local-agent-foundry-local.ipynb)。单元格 7 创建项目、8 定义工具；编号为包含 Markdown 的零基数组下标。

固定版本的[模块 README](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/17-creating-local-ai-agents/README.md)只配有这一份 Python notebook，没有 .NET notebook。它包含本地工具/RAG 主线和 `LOCAL_MCP_COMMAND` 可选分支；持久记忆、多 MCP 与双代理是扩展作业，不是另有未列出的源码 notebook。本地路线不需要云端 `.env`；不使用 MCP 时保持该可选变量不存在，不设置为 `...`。

先创建练习目录：

```powershell
New-Item -ItemType Directory -Force -Path .\lab-work\17-local | Out-Null
```

把下面代码保存为 `lab-work\17-local\tools_check.py`。它提取固定源单元格 8 的函数定义，但不执行源 manager、模型请求或 Chroma。`auth.py` 使用教学占位实现，故意不实现认证；不能用于实际登录。

```python
import ast
import json
from pathlib import Path

ROOT = Path(r"lab-work\17-local\sample_project").resolve()
ROOT.mkdir(parents=True, exist_ok=True)
fixtures = {
    "auth.py": (
        "def login(user, password):\n"
        "    # TODO: implement approved authentication\n"
        "    return False\n\n"
        "def logout(session):\n"
        "    session.clear()\n"
    ),
    "utils.py": (
        "def clamp(value, low, high):\n"
        "    return max(low, min(value, high))\n"
    ),
}
for name, text in fixtures.items():
    target = ROOT / name
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise RuntimeError(f"Refusing to overwrite changed fixture: {name}")
    target.write_text(text, encoding="utf-8")

source = Path(
    r"17-creating-local-ai-agents\code_samples\17-local-agent-foundry-local.ipynb"
)
nb = json.loads(source.read_text(encoding="utf-8"))
tree = ast.parse("".join(nb["cells"][8]["source"]))
names = {"_safe_path", "list_files", "read_file", "analyze_code"}
defs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
scope = {"Path": Path, "json": json, "PROJECT_ROOT": ROOT}
exec(compile(ast.Module(body=defs, type_ignores=[]), str(source), "exec"), scope)
assert scope["_safe_path"]("auth.py") == ROOT / "auth.py"
assert scope["_safe_path"](r"..\outside.txt") is None
assert scope["_safe_path"](str(ROOT.parent / "outside.txt")) is None
assert scope["read_file"](r"..\outside.txt").startswith("Access denied")
assert scope["read_file"]("absent.py").startswith("No such file")
metrics = json.loads(scope["analyze_code"]("auth.py"))
assert metrics["functions"] == 2 and metrics["todos"] == 1
assert set(scope["list_files"]().split(", ")) == {"auth.py", "utils.py"}
print("TOOLS PASS: 2 functions, 1 TODO; outside paths refused")
```

运行：

```powershell
python .\lab-work\17-local\tools_check.py
```

通过标准是所有断言成立、退出码为 0；越界测试仅构造路径，**不会创建或读取目录外文件**。测试目录不得包含 symlink/junction。这个 AST 白名单读取器仅用于本固定源码，不是任意不可信程序的隔离沙箱。

## 步骤二：添加有边界的 TODO 工具

在练习 notebook 或 `tools_check.py` 中复用 `ROOT`，增加以下工具。只扫描允许扩展名和小文件，逐个解析路径；将打印的源码行替换为简洁命中位置，减少内容暴露。

```python
def find_todos():
    hits = []
    for path in ROOT.rglob("*"):
        resolved = path.resolve()
        if ROOT not in resolved.parents or path.is_symlink():
            continue
        if not resolved.is_file() or resolved.suffix not in {".py", ".md"}:
            continue
        if resolved.stat().st_size > 64 * 1024:
            continue
        for number, line in enumerate(
            resolved.read_text(encoding="utf-8").splitlines(), 1
        ):
            if "TODO" in line or "FIXME" in line:
                hits.append({"file": str(resolved.relative_to(ROOT)), "line": number})
    return hits

assert find_todos() == [{"file": "auth.py", "line": 2}]
```

若目录中后来加入其他文档，改为检查预期记录是否包含于结果，而非删除定位校验。通过标准是给出相对文件与正确行号，并拒绝沙箱外输入；不把 TODO 字样当成已完成代码安全审查。

## 步骤三：可选连接已准备好的 Foundry Local

本节开始才需要模型；没有本地运行环境时保留工具演练结果，将模型相关项目标为待演练。接收方在下载前批准并准备：

- Microsoft Foundry Local Windows 运行时和支持的硬件驱动。
- `qwen2.5-7b-instruct` 对应的可用本地构建与实际磁盘空间；目录变化时应记录替代型号和工具调用验证结果。
- Python `foundry-local-sdk`、`openai`、`chromadb`；安装方式遵循环境章和根 requirements。
- 严格离线班级需预缓存推理权重与 Chroma 嵌入权重，检查遥测/出站策略。

只有在准备阶段获准后才使用原文的安装/运行命令：

```powershell
winget install Microsoft.FoundryLocal
foundry model run qwen2.5-7b-instruct
foundry service status
```

`foundry model run` 可能下载并进入交互模式，按 CLI 的退出提示结束交互后再检查服务。它不是内容交付阶段要执行的步骤。不要同时重复启动多份服务，不猜测固定端口。

在练习 notebook 中使用源单元格 4，并增加 endpoint 检查：

notebook 的 kernel 工作目录也必须是仓库根目录，不一定等于 notebook 保存位置。先用 `Path.cwd()` 确认，并检查 `Path("17-creating-local-ai-agents").is_dir()`；不满足时在编辑器中将 kernel 工作目录切换到实际源码根，不把 `sample_project` 建在个人目录。本章后续 `lab-work` 路径都相对该根目录。

```python
from urllib.parse import urlparse
from foundry_local import FoundryLocalManager
from openai import OpenAI

MODEL_ALIAS = "qwen2.5-7b-instruct"
manager = FoundryLocalManager(MODEL_ALIAS)
model_info = manager.get_model_info(MODEL_ALIAS)
assert urlparse(manager.endpoint).hostname in {"localhost", "127.0.0.1", "::1"}
client = OpenAI(base_url=manager.endpoint, api_key=manager.api_key, timeout=60)
MODEL_ID = model_info.id
```

实例化 manager 本身可能启动/下载；不满足前提时不要执行。记录实际模型 ID、硬件、包版本和服务状态，不记录占位 key。按源单元格 5 发一条无敏感信息的问题，收到非空回答只证明本地模型可响应，尚未证明工具调用。

## 步骤四：建立可验证的本地 RAG

先理解源码单元格 10：四段 `DOCS`、`chromadb.Client()`、`search_docs(..., n_results=2)`。主线可保留内存方式，预期重启后集合消失；不要写成持久化成功。

选择持久化变体时，在练习 notebook 中从源单元格 10 复制 `DOCS` 字典，使用下面初始化替换原客户端：

```python
import chromadb
from chromadb.config import Settings
from pathlib import Path

db_path = Path(r"lab-work\17-local\chroma").resolve()
chroma_client = chromadb.PersistentClient(
    path=str(db_path), settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_or_create_collection("project_docs")
collection.upsert(ids=list(DOCS), documents=list(DOCS.values()))
assert collection.count() == 4
```

**首次 `upsert/query` 可能下载默认嵌入模型。** 关闭 Chroma 匿名遥测不自动关闭系统、其他 SDK 或模型运行时的所有网络活动。严格离线必须由接收方验证依赖缓存和网络策略；禁止失败时偷偷切换云嵌入。

复用源 `search_docs`，先直接查 `how are passwords handled?`，核对返回的证据来自 `DOCS`，再交给模型。原 `DOCS` 对应原始不安全认证示例，与本章占位 `auth.py` 不完全一致；若使用本章文件，更新 `auth` 文档为“尚未实现认证，当前返回 False”，避免让过期文档与文件相互矛盾。

持久化通过条件：关闭使用该集合的 Python 进程，再在相同路径重新连接，集合仍有四条且能检索；不是同一进程重复查询。如果改用真实文档扩展，至少五个经批准的小文件、每条保存相对来源、稳定 ID、明确更新/删除规则，禁止递归索引仓库所有文件或秘密配置。

## 步骤五：把工具接入本地模型循环

在练习 notebook 中按顺序定义：

1. 项目根路径和源单元格 8 的四个本地函数；确保 `PROJECT_ROOT = ROOT.resolve()`。
2. 源单元格 10 的 `search_docs`，绑定刚创建的集合。
3. 源单元格 12 的 `TOOLS_SCHEMA`、`TOOL_IMPL`；新增 `find_todos` 时两处都注册，不能只定义 Python 函数。
4. 源单元格 13 的 `run_agent`；保持 `max_iterations=5`，遇未知工具或异常参数停止并记录，不给通用 shell 作为备用工具。

工具回传的关键形状：

```python
messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "content": str(result),
})
```

每条结果必须对应该轮的调用 ID，不能把多个工具返回串成一个没有来源的消息。源 `json.loads` 和函数调用没有完整异常兜底；在练习副本加入格式校验与有限错误返回，再做坏 JSON、未知工具和错误路径的直接测试。

用三个问题验证不同路径：

- “根据文档，这个项目当前如何处理认证？”：应展示 RAG 来源，不假装读取过文件。
- “读取 auth.py，说明两个函数当前做什么。”：必须有 `read_file` 调用证据。
- “项目有哪些 TODO？给出相对文件和行号。”：必须使用新增工具并返回预期位置。

用 `time.perf_counter()` 记录每次实际响应时长与工具次数；没有测量前不填写数字。工具名/参数形状/返回摘要可以作为证据，但不记录真实文件全文。遇五轮停止文本时记为未完成，不调高到无上限。

## 步骤六：可选只读本地 MCP

源单元格 18 未设置 `LOCAL_MCP_COMMAND` 时跳过，这本身是有效的可选分支。设置后它只列工具；含空格的 Windows 路径会被 `command.split()` 错拆。不要照搬未经固定版本的 `npx -y` 下载执行方式。

需要实际本地协议演练时，将以下服务器保存为 `lab-work\17-local\mcp_readonly.py`，只公开固定虚构说明，不提供任意文件或 shell 功能：

```python
from mcp.server.fastmcp import FastMCP

server = FastMCP("training-readonly")

@server.tool()
def project_summary() -> str:
    return "Training project: auth.py and utils.py; no production data."

if __name__ == "__main__":
    server.run(transport="stdio")
```

在练习 notebook 中使用显式可执行文件和参数数组，不拼接命令字符串：

```python
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(r"lab-work\17-local\mcp_readonly.py").resolve())],
)
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        names = [t.name for t in (await session.list_tools()).tools]
        assert "project_summary" in names
        result = await session.call_tool("project_summary", {})
        assert not result.isError
        assert any("Training project" in getattr(c, "text", "") for c in result.content)
```

在普通 `.py` 中应包装为 `async def main()` 后 `asyncio.run(main())`，不能直接放顶层 `await`。通过条件为本地子进程启动、列出受限工具、返回固定文本、离开上下文后子进程结束。它不调用模型；要加入 Agent 工具循环，还需显式桥接调用、验证工具模式与超时，不能把“列出工具”写成“模型已使用 MCP”。

## 步骤七：混合、记忆与多代理扩展

主线保持本地。先用纯函数做混合决策，不发任何云请求：

```python
def route(*, sensitive, offline, complex_task, cloud_allowed):
    if sensitive or offline or not cloud_allowed:
        return "local"
    return "cloud" if complex_task else "local"

assert route(sensitive=True, offline=False, complex_task=True, cloud_allowed=True) == "local"
assert route(sensitive=False, offline=False, complex_task=True, cloud_allowed=True) == "cloud"
assert route(sensitive=False, offline=True, complex_task=True, cloud_allowed=True) == "local"
```

通过条件是敏感/断网路径不外发；云故障时降级到本地或拒绝。这里的 cloud 只是标签，不是已经实现的模型回退。

进一步可选：

- **本地记忆**：在练习目录持久化经过脱敏的简短历史，重启后问一个先前事实；验证只读取当前会话记录、有删除路径，不保存秘密或工具全文。
- **多个 MCP 服务**：为每个服务指定独立显式参数和工具前缀，避免同名工具误路由；一个失败不扩大另一个权限。
- **本地双代理**：工程助手给出基于工具的草稿，审阅者检查证据；使用同一只读沙箱与总迭代预算。审阅者必须能指出一个故意放入的无依据断言，不能以两个模型一致作为真实性证明。

文档审阅器作业要求至少五个获准文件、TODO 工具、三类问题与实际延迟记录，并说明哪些数据即使复杂也不能上云。

## 故障排查

| 现象 | 检查与恢复 |
| --- | --- |
| 模型别名不可用或内存不足 | 核实本地目录、硬件构建和空闲资源；更换需记录型号及重新验证，不默认下载更大模型 |
| endpoint 不是回环地址 | 停止调用并纠正配置，不把敏感文件发向该地址 |
| 首次 RAG 在断网时失败 | 嵌入权重未缓存；由接收方准备，不切云端嵌入 |
| 文档与文件矛盾 | 核对 `DOCS` 是否仍描述原示例，更新来源版本与内容 |
| 工具 JSON 错或五轮耗尽 | 保存脱敏错误，补参数验证、缩小问题，不取消预算 |
| MCP Windows 启动失败 | 使用 `sys.executable` 与 `args` 数组，检查依赖和脚本路径 |

## 清理与预期结果

关闭客户端、notebook kernel、MCP 会话；只停止本次拥有的本地服务，共享 Foundry Local 服务须保留。服务 CLI 管理命令应先查当前安装版本帮助，不猜测清理命令或按名字杀所有进程。推理和嵌入模型缓存如共享则保留。

**删除前警告：** 持久向量库和记忆可能包含文档内容。确认 `lab-work\17-local` 仅含本次虚构练习后预览：

```powershell
Remove-Item -LiteralPath .\lab-work\17-local -Recurse -WhatIf
```

核实后才去掉 `-WhatIf`。不要删除源 lesson 或共享模型目录。

预期交付是：工具正反例、模型实际 ID（如运行）、RAG 来源与持久化证据、三问题的工具记录、MCP 选择分支和混合边界说明。纯本地路线没有 Foundry hosted Responses endpoint，不运行第 16 模块的云端 smoke test。

**演练状态：待演练。** 当前没有模型下载、推理、浏览器或云调用；接收方后续记录日期、版本、硬件、实际延迟、断言与离线性检查结果。继续[签名收据概念](18-concepts.zh-CN.md)。
