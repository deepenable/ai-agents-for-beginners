# 准备固定版本的实验环境

## 目标与准备

本章对应源课程 00。目标是取得可追溯源码、选择正确 Python 内核、配置最少必要变量，并在第一次模型调用前确认身份、权限和费用。目标教学环境为 **Windows 11、PowerShell 7、Python 3.12+**；Git 建议 2.25+ 以支持稀疏检出。VS Code 的 Python 和 Jupyter 扩展是可选编辑界面，也可使用 JupyterLab。

先安装上述工具；云端路线另需 Azure CLI、自备的开发订阅及资源所有者提供的实验项目。不要申请生产管理员密码。具体 Azure CLI、编辑器、SDK 和模型实际版本须在演练时记录；本手册不声称已经在这些版本组合上实测成功。

**风险提示：安装依赖会联网；云端模型调用、Search、Bing、托管运行及 Codespaces 可能计费。所有资源使用须经过预算批准。不要在生产项目中测试工具写入、删除或权限变更。**

## 步骤一：取得课程源码

配套源码固定在 fork 的实际提交 `25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595`。这是本次内容适配的**输入源码版本**，不是未来包含交付文件的发布提交。

在专门存放实验的父目录打开 PowerShell，执行以下命令。目录 `ai-agents-lab-source` 应尚不存在；不要在已有工作目录里覆盖或切换未保存的代码。

```powershell
git clone --filter=blob:none --no-checkout --sparse https://github.com/deepenable/ai-agents-for-beginners.git ai-agents-lab-source
Set-Location ai-agents-lab-source
git sparse-checkout set 00-course-setup 01-intro-to-ai-agents 02-explore-agentic-frameworks 03-agentic-design-patterns 04-tool-use 05-agentic-rag 06-building-trustworthy-agents 07-planning-design 08-multi-agent 09-metacognition 10-ai-agents-production 11-agentic-protocols 12-context-engineering 13-agent-memory 14-microsoft-agent-framework 15-browser-use 16-deploying-scalable-agents 17-creating-local-ai-agents 18-securing-ai-agents scripts tests
git checkout --detach 25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595
git rev-parse HEAD
```

预期最后一行严格等于上述 40 位值。每条 Git 命令均应成功后再继续。稀疏检出保留根文件和全部正式模块，不下载无关语言与翻译素材。保留 `.git`：它是版本核对和追溯依据，不是应清理的实验垃圾。

源码入口：[环境准备原文](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/00-course-setup/README.md)、[依赖清单](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/requirements.txt)。各章链接均使用此版本，文件在浏览器中只供阅读；运行要使用本地副本。

## 步骤二：创建隔离解释器

工作目录仍是源码仓库根。先确认本机 Python 启动器能找到 3.12；若使用更新版本，将命令中的 `-3.12` 换成实际已安装的版本。

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install nbconvert ipykernel
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import sys; from importlib.metadata import version; print(sys.version.split()[0]); print(version('agent-framework-core'))"
```

预期：Python 不低于 3.12；`agent-framework-core` 为 `1.10.0`；`pip check` 不报告不兼容依赖。此处只安装和检查，不调用模型。

仓库对 `agent-framework-core==1.10.0`、Foundry/OpenAI 集成 `~=1.10.0` 有约束，不要用 `pip install -U agent-framework` 替换。其他依赖未全部锁定；首次演练请把 `pip freeze` 的去敏结果交给接收方作为环境记录，而不要声称已有全依赖锁定环境。

在 VS Code 打开源码根目录及需要的 `.ipynb`，右上角选择此 `.venv` 的 Python 内核。新增一个临时检查单元格运行：

```python
import sys
print(sys.executable)
```

预期解释器位于本次源码目录下的 `.venv`。此路径只在自己屏幕上查看，交付记录不要保留包含个人用户名的完整路径。运行 notebook 自带的安装单元格前先核对是否会升级已约束依赖；必要时跳过重复安装单元格，并如实记录原因。

不使用 VS Code 时，可在同一虚拟环境安装并启动 JupyterLab：

```powershell
.\.venv\Scripts\python.exe -m pip install jupyterlab
.\.venv\Scripts\python.exe -m jupyterlab
```

这会启动本机服务。不要把包含访问令牌的启动 URL、日志或截图上传到作业，也不要把服务暴露到公网。

## 步骤三：确认云资源与身份

先让资源所有者确认以下事项，再登录自己的开发账号：

| 主线路径 | 必要资源与权限 |
| --- | --- |
| Foundry 项目智能体 | 支持当前示例 Agent Service 接口的项目、已部署模型和配额；对实验项目有调用模型及管理实验智能体所需的数据权限，通常由管理员按项目范围配置 Azure AI User 等适用角色 |
| 直接 Azure OpenAI | Azure OpenAI 资源、支持示例所用 Responses 或 Chat Completions 能力的部署；密钥方式或被批准的 Entra 数据权限，不能仅凭订阅读取权限调用 |
| 05/16 可选 Azure AI Search | 独立测试索引、写入和查询权限；具体例子采用 RBAC 或密钥的区别见对应实践章节 |
| 其他拓展 | 08 Bing 连接、11 GitHub MCP、13 外部记忆后端、15 浏览器、17 本地模型等按章单独准备 |

项目端点从 [Microsoft Foundry 门户](https://ai.azure.com)的项目概览取得；模型部署名从该项目已部署模型列表取得。新建项目或模型前阅读价格、区域和配额，使用资源所有者批准的部署方式；旧教程中的 hub 菜单并不适用于所有新门户界面。不要仅为消除 403 给自己授予整个订阅 Owner。

```powershell
az version
az login
az account show --query state -o tsv
```

在自己的屏幕确认登录的是被批准订阅；如不一致，先用 Azure CLI 选择正确订阅。预期状态为 `Enabled`。登录成功只证明身份可用，**不证明模型、项目数据权限或配额足够**；实际调用由后续章节判定。

无浏览器环境可自行运行 `az login --use-device-code`，但不要把设备码、二维码或邀请信息粘贴到课程平台。`DefaultAzureCredential` 还可能选中环境或托管身份，不总是使用 CLI 身份；401/403 时按实际代码中的凭据类型排查。

## 步骤四：配置最少必要变量

在源码仓库根用本地编辑器创建 `.env`。若文件已经存在，先审查并仅修改本实验所需项，不覆盖他人的配置。大多数 Foundry 主线仅需以下内容：

```dotenv
AZURE_AI_PROJECT_ENDPOINT=https://<project-resource>.services.ai.azure.com/api/projects/<project-name>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<deployed-model-name>
```

`<project-resource>`、`<project-name>` 和 `<deployed-model-name>` 都须换成自己已批准资源的实际值。模型部署名不是模型系列名的同义词，应与门户中的部署名一致。

[原始环境变量说明](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/.env.example)列出了可选配置。**不要把样例中的 `...` 当作可用密钥，也不要保留未使用服务的非空占位符。** 部分代码只判断环境变量是否非空，虚假的 Search、MiniMax 或其他密钥可能错误触发收费后端或认证失败。

| 变量 | 何时填写及从哪里取得 |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_DEPLOYMENT` | 直接 OpenAI 示例；Azure OpenAI 资源的端点和部署名 |
| `AZURE_OPENAI_API_KEY` | 仅在实际代码使用密钥认证时；通过资源所有者约定的安全渠道获取，不放入输出 |
| `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | 15 浏览器示例使用的聊天模型部署名 |
| `AZURE_SEARCH_SERVICE_ENDPOINT` / `AZURE_SEARCH_API_KEY` | 16 真实 Search 分支需同时存在；默认不填以使用内存知识库。05 可选索引路线按其单独步骤 |
| `BING_CONNECTION_ID` | 08 条件工作流可选路线，从项目连接资源取得；不是免费、自动创建的连接 |
| `AZURE_AI_SMALL_MODEL` / `AZURE_AI_LARGE_MODEL` | 16 需要真实比较两级路由时，填写项目中已存在的两个部署名 |
| 其他服务变量 | 只按对应章实际读取的名称填写；替代供应商不保证与全部示例 API 功能等价 |

用虚拟环境 Python 只检查是否填写，避免打印值：

```powershell
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; load_dotenv(); names=['AZURE_AI_PROJECT_ENDPOINT','AZURE_AI_MODEL_DEPLOYMENT_NAME']; print({n: bool(os.getenv(n)) and '<' not in os.getenv(n, '') and os.getenv(n) != '...' for n in names})"
git check-ignore .env
```

预期两个布尔值都为 `True`，并且 Git 将 `.env` 识别为被忽略文件。此检查不会联网，不能证明端点有效。Git 忽略也不是秘密保护机制：仍不能上传 `.env`、访问令牌或带秘密的 notebook 输出。

## 步骤五：选择首个实验并记录

打开 01 的 Python notebook，逐单元格阅读，确认工具只是课程示例且没有真实采购动作。再按[首次智能体实践](01-practice.zh-CN.md)执行。每次先完成资源和风险说明，再运行调用单元格；失败立即停在该单元格排查，不连续重试造成费用。各章明确说明其单元格编号从 0 还是从 1 开始，均包含 Markdown；它们不是界面的执行计数。优先结合函数名或段落标题定位，不把不同章节的编号习惯混用。

仓库自带[notebook 检查脚本](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/scripts/validate-notebooks.ps1)。准备阶段只能先列清单：

```powershell
.\scripts\validate-notebooks.ps1 -Python .\.venv\Scripts\python.exe -List
```

预期列出 Python 示例而不执行。去掉 `-List` 会实际调用服务并可能写入文件和计费；交互式审批示例也不适合未经检查的一键全跑。此脚本检查配套代码，**不是平台课程清单的正式验证器**。

## 可选路线与差异

源课程的 .NET 样例使用 .NET 10+，部分是可直接运行的 file-based `.cs`，部分是 .NET Interactive notebook；参考对应模块，不把 Python 内核用于 .NET。记录 SDK 及实际 NuGet 解析版本。

MiniMax/Novita 等服务需要自备账号、密钥和单独预算。源代码并非全部自动读取这些变量，例如 Novita 需要显式传入客户端；本次交付不承诺替换端点即可运行整套课程。17 的 Foundry Local 走本地 OpenAI 兼容接口，不能代替所有云端 Responses/Agent Service 功能。

Azure AI Search 补充材料包含存储、索引、RBAC 和 .NET 路线，但 **05/16 的内存主线不要求先建 Storage 或 Search**。需要可选索引实验时再阅读[固定版本 Search 指南](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/00-course-setup/AzureSearch.md)，同时遵守 05 实践中的版本与索引风险说明。

## 常见故障与恢复

| 现象 | 排查与恢复 |
| --- | --- |
| 找不到 `py -3.12` | 安装受支持 Python；重新打开终端，再以实际解释器创建新虚拟环境，不在旧 3.11 环境强装课程 |
| import 失败或 `ChatMessage` 等 API 不存在 | 核对 notebook 内核、源提交和 `pip check`；按本章固定依赖重建实验虚拟环境，不升级整个框架试错 |
| 环境变量看似存在仍报端点/密钥错误 | 检查工作目录、是否载入根 `.env`、是否仍为 `...`、是否被进程已有环境变量覆盖；修改后重启内核 |
| 401/403 | 检查实际凭据链、租户/订阅、项目范围的数据角色和端点类型；交给资源管理员核对，不粘贴令牌 |
| 404/不支持的 API | 区分项目端点和 Azure OpenAI 端点；核对部署名与模型所支持 API，不盲目拼接不同 SDK 的路径 |
| 429/配额不足 | 停止批量运行，查看配额与错误中的退避提示；先降低并发，再由负责人决定配额或预算 |
| TLS 证书错误 | 修复系统/企业代理 CA 信任和 Python 证书配置；不要关闭证书验证 |

## 预期结果与演练记录

合格的准备结果应同时满足：源码 SHA 一致、Python 版本满足要求、依赖无冲突、内核属于隔离环境、配置检查不输出秘密、CLI 身份与资源授权经本人确认。记录日期、OS、Python、Azure CLI、核心依赖和具体模型部署版本；没有实际执行的项写“未执行”。

**教学演练状态：待演练。** 本章没有宣称模型调用成功，也不替代接收方的正式平台导入检查。

## 清理

停止 Jupyter 服务和 notebook 内核，确认没有后台任务。实验后按需 `az logout`，特别是在共享设备；不要登出他人的会话。仅删除自己创建的临时 notebook 输出和不再需要的 `.env`，共享凭据的撤销由所有者处理。

虚拟环境和源码可保留用于后续课程，不必删除；若要移除，先确认目标是自己的独立实验副本。不要删除整个共享目录、`.git` 或云资源组。已部署模型、索引和智能体会跨 notebook 存活，最终必须按对应实践章核对并清理。
