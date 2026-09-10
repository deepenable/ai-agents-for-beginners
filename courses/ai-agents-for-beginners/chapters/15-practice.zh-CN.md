# 在本地卡片上演练浏览器提取与安全比价

## 学习目标

在不登录网站、不预订住宿的条件下，练习 Playwright 的可控操作、Pydantic 结构校验和确定性价格计算；再把这些边界映射到源笔记本的 Browser-Use 视觉流程。

主线使用手册内的虚构卡片，并不是 Airbnb 页面复刻，也不是视觉模型测试。云端扩展另行演练，两条路线的结果不可混为一谈。

## 准备、费用和权限警告

先完成[环境准备](00-setup.zh-CN.md)，并阅读[浏览器概念](15-concepts.zh-CN.md)。以下命令工作目录为固定版本源码仓库根目录，使用 Windows、PowerShell 7、Python 3.12+ 和该源码的虚拟环境；源码文件只读，练习文件放在 `lab-work\15-browser`。

**执行前警告：** 安装软件和浏览器需要网络、磁盘空间及本机软件安装授权；本地路线不产生模型费用。可选云端路线会发送页面文本/截图并计费，只允许接收方批准后使用培训资源。不得提供生产凭据、个人 cookie、支付信息或真实客户资料。涉及交易的按钮一律不执行。

基础依赖沿用[仓库 requirements](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/requirements.txt)，不要运行 notebook 中无版本约束的全框架升级单元格。其关键约束为 `agent-framework-core==1.10.0`、Foundry/OpenAI 集成 `~=1.10.0`；并非所有间接依赖都精确锁定。

本模块额外的浏览器依赖不在根 requirements 中：

```powershell
python -m pip install playwright pydantic
python -m playwright install chromium
python -m pip check
New-Item -ItemType Directory -Force -Path .\lab-work\15-browser | Out-Null
```

只准备云端视觉扩展时再安装下列包并记录解析版本。源单元格 2 还列了 `langchain-openai`，但当前导入实际使用 Browser-Use 自带的 Azure 客户端，不依赖该 LangChain 客户端。

```powershell
python -m pip install browser-use aiohttp
python -m pip show browser-use playwright pydantic aiohttp
```

上游没有给这组浏览器依赖提供完整版本锁，接收方应保存实际包版本并验证兼容性，不凭空填写“已验证版本”。安装失败先处理环境，不持续升级课程固定的 Agent Framework 核心包。

## 步骤一：只读定位源代码

参考[完整源笔记本](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/15-browser-use/15-browser-user.ipynb)。零基单元格 9 是提取模式，18 是最后生效的 `AirbnbSearchAgent`，19 是会直接启动浏览器并调用模型的入口。**不要 Run All。**

固定版本的[模块 README](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/15-browser-use/README.md)只列这一份 Python notebook，没有 .NET notebook。单元格 16 的 Playwright browser 包装与单元格 18 的 CDP 连接是同一文件内的不同实现；本手册以最后生效的 CDP 版本作为云端扩展，并以前面的本地 Actor 练习覆盖确定性控制。

```powershell
$nb = Get-Content .\15-browser-use\15-browser-user.ipynb -Raw | ConvertFrom-Json
foreach ($i in 9, 18) {
    "CELL $i"
    $nb.cells[$i].source -join ''
}
```

此命令只读取 JSON，不执行其中 Python。检查类构造函数确实使用 `cdp_url`，并找出 `search_agent.run()`、`page.extract_content` 两次不同用途的模型相关步骤。

## 步骤二：建立不允许外网请求的本地 Actor

在 `lab-work\15-browser\local_cards.py` 保存下面完整代码。HTML 仅作为代码里的本地测试夹具，页面没有外部图片、脚本、链接目标或表单提交端点。代码默认创建无个人登录态的浏览器上下文，并拒绝所有网络请求。

```python
import asyncio
import math
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright

class Listing(BaseModel):
    title: str
    price_per_night: float = Field(gt=0)
    currency: str

PAGE = """
<!doctype html>
<html lang="en"><body>
<h1>Training stays</h1>
<button id="show" type="button">Show prices</button>
<p id="notice">Read-only comparison. No booking is available.</p>
<article class="card" data-price="900" data-currency="SEK">North</article>
<article class="card" data-price="650" data-currency="SEK">Harbor</article>
<article class="card" data-price="800" data-currency="SEK">Park</article>
</body></html>
"""

def compare(listings):
    if not listings:
        raise ValueError("No comparable listings")
    if len({x.currency for x in listings}) != 1:
        raise ValueError("Mixed currencies")
    if not all(math.isfinite(x.price_per_night) for x in listings):
        raise ValueError("Non-finite price")
    return min(listings, key=lambda x: x.price_per_night)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            await context.route("**/*", lambda route: route.abort())
            page = await context.new_page()
            await page.set_content(PAGE)
            await page.get_by_role("button", name="Show prices").click()
            assert page.url == "about:blank"
            cards = page.locator("article.card")
            assert await cards.count() == 3
            listings = []
            for card in await cards.all():
                listings.append(Listing(
                    title=await card.inner_text(),
                    price_per_night=await card.get_attribute("data-price"),
                    currency=await card.get_attribute("data-currency"),
                ))
            best = compare(listings)
            assert (best.title, best.price_per_night, best.currency) == (
                "Harbor", 650.0, "SEK"
            )
            print("LOCAL PASS: 3 cards; Harbor; 650 SEK/night; no booking")
            for bad in ([], [listings[0], Listing(
                title="Other", price_per_night=1, currency="USD"
            )]):
                try:
                    compare(bad)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Unsafe comparison accepted")
            print("NEGATIVE PASS: empty and mixed-currency results refused")
        finally:
            await browser.close()

asyncio.run(main())
```

执行：

```powershell
python .\lab-work\15-browser\local_cards.py
```

预期出现两条 `PASS` 文本且退出码为 0。它们是**应当获得的结果，不是已演练结果**。按钮只演练定位与点击，没有购买或提交副作用；卡片读取和价格比较不调用模型。把夹具价格改为其他正数时，应同时调整确定性的期望最小值，不能只删除断言。

## 步骤三：为“模型提取”补上模型外校验

对照源单元格 9，把本地 `Listing` 扩展为原始的 `AirbnbListing` 字段集合；保留价格正数约束，不把默认 `SEK` 当作验证。构造三条虚构记录后检查：

1. `total_listings_found == len(listings)`。
2. 列表非空，价格为有限正数，币种和日期口径一致。
3. `cheapest_listing` 属于列表，价格等于 Python `min` 的结果。
4. `average_price` 等于 Python 重算的平均值，按明确的小数精度比较。
5. 若扩展到网站链接，用 `urllib.parse.urlparse` 验证 HTTPS、准确主机名及 `/rooms/` 路径，不使用字符串包含 `airbnb` 的弱判断。

源流程的链接可为空；不可凭空拼出房源 URL。未知总价、税费或日期时，结果写“仅比较已见每晚价格，不能确定完整住宿成本”。通过条件是至少一个错误数量、一个混合币种、一个虚假的最低价被拒绝，而不是仅打印漂亮表格。

## 步骤四：可选的 CDP 与云端视觉路线

本节由接收方在培训资源和站点许可均准备好后实施；当前交付不启动真实浏览器代理、不访问 Airbnb、不调用模型。

### 资源和凭据

需要具有视觉输入和工具调用能力的 Azure OpenAI 部署、培训资源 endpoint、部署名，以及 Browser-Use 支持的认证配置。源单元格 5、7 使用：

| 变量 | 获取与用途 |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | 培训 Azure OpenAI 资源的 endpoint，不是 Foundry project endpoint |
| `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | 接收方实际部署名，不是随意填写的模型系列 |
| `AZURE_OPENAI_API_KEY` | 经批准的培训密钥，经安全渠道设置，不打印、不提交 |
| `AZURE_OPENAI_API_VERSION` | 资源和当前 Browser-Use 客户端支持的版本；不要猜测 |

“默认最新 API 版本”是源说明，不是可复现配置。演练时记录明确、支持的版本。源码打印 endpoint 的单元格可在练习副本中改为仅报告是否设置，不导出环境文件或秘密值。

按[环境准备](00-setup.zh-CN.md)建立只含已选路线所需字段的最小配置。不要复制完整 `.env.example` 后保留可选项的 `...`：它是非空字符串，会被许多 SDK 或布尔检查视为“已配置”。未采用的可选配置应移除；不要把省略号当作有效 API 版本、部署名或密钥。

### Windows 启动修正与明确停机

源单元格 19 的启动器依赖 PATH 上的 Chrome，并创建系统临时配置目录。练习副本应改为本仓库的 `lab-work\15-browser\profile`，不使用个人目录或系统临时目录；使用 Playwright 已安装 Chromium 的真实路径可避免 PATH 猜测。

下面代码只说明如何在另一个练习副本中准备专用 CDP 浏览器；不得在尚未批准的机器上执行。确认 9222 无其他服务占用后启动，保留返回的进程对象，不用按进程名批量结束 Chrome。

```python
from pathlib import Path
import subprocess
import urllib.request
import json
import time
from playwright.sync_api import sync_playwright

profile = Path(r"lab-work\15-browser\profile").resolve()
profile.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    chromium = p.chromium.executable_path
proc = subprocess.Popen([
    chromium,
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=9222",
    f"--user-data-dir={profile}",
    "--no-first-run",
    "about:blank",
])
try:
    ready = False
    for _ in range(20):
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:9222/json/version", timeout=1
            ) as response:
                ready = bool(json.load(response).get("webSocketDebuggerUrl"))
            if ready:
                break
        except (OSError, ValueError):
            time.sleep(1)
    if not ready:
        raise RuntimeError("CDP not ready; do not start the agent")
    print("CDP ready; training profile only")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
```

这段独立探针会立即清理浏览器；不是让它在退出后继续运行。真正整合源 `main` 时，将**已批准的搜索与提取**放在同一 `try` 内并保留 `finally`；异步笔记本用其 `async_playwright` 等价写法，不能在同一事件循环混用同步 API。

### 受限执行与验收

1. 在练习副本保留单元格 4、7、9、18 的有效定义，跳过被覆盖的单元格 16 和未使用的 booking 模型。以单元格 19 作为生命周期参考，不复制其 HTML 展示。
2. 用 `Browser(cdp_url="http://127.0.0.1:9222", keep_alive=True)` 连接专用实例；确认 Browser-Use 与 Playwright 看到同一个页面。不要把 `pages[0]` 无条件当作活动结果页，先验证 URL。
3. 搜索仅限获准页面、Stockholm 房源和明确日期。禁止登录、消息、预订和付款；遇验证码、权限或站点限制就停止，不尝试绕过。网站子资源所需域名也须审查，提示词白名单不能代替网络与导航策略。
4. 把无界 `await search_agent.run()` 改为受限调用，例如 `await asyncio.wait_for(search_agent.run(max_steps=8), timeout=120)`，并为提取设置同类超时。数字是本练习的预算，不是承诺运行时长。
5. 只读取当前可见且价格清晰的卡片，然后执行步骤三的校验；验证失败时不显示“最低价已找到”。不要自动重试到额度耗尽。
6. 记录实际动作数量、卡片数量、脱敏的结果摘要和退出原因。成功标准为允许范围内完成只读提取、结果可核验、资源已关闭；不是固定房源、固定价格或无条件绿色输出。

源代码会使用 `get_pages`、`extract_content` 等 Browser-Use API，它们与 Playwright `Page` 不是同一接口。若当前依赖不支持这些方法，应记录兼容性阻塞并停留在本地路线；不要把纯文本抓取冒充视觉流程已验证。

## 故障排查

| 现象 | 检查顺序与恢复 |
| --- | --- |
| Playwright 找不到可执行文件 | 确认同一 Python 环境，执行 `python -m playwright install chromium`，再查安装权限 |
| CDP 不就绪或端口冲突 | 查 9222 是否已被使用，停止本次创建的进程；不要连接未知浏览器 |
| `Browser` 参数或 `extract_content` 不存在 | 对照安装版本与单元格 18；登记未锁定浏览器依赖造成的兼容问题 |
| 页面无价格或出现登录/验证码 | 停止云端路线，使用本地夹具；不要输出猜测值 |
| 401/403 或模型能力错误 | 区分资源 endpoint、部署名、认证与模型能力；由接收方核查，不扩大权限 |
| 模型输出最低价与列表不符 | 以 Python 重算结果为准并标记提取错误，不继续预订 |

## 清理

先关闭本实验浏览器上下文、Playwright 实例和记录的 CDP 进程。仅在确认不再占用且目录只含本次练习内容后，预览删除：

```powershell
Remove-Item -LiteralPath .\lab-work\15-browser -Recurse -WhatIf
```

这是删除操作；核实路径后再去掉 `-WhatIf`。不要清理个人浏览器目录或其他人正在使用的环境。已安装 Chromium 可保留供后续课程，不强制删除共享缓存；云端扩展的训练密钥由接收方按保留策略撤销，不把长期密钥留在 notebook 输出。

## 预期交付与演练记录

- 本地路线两条断言组通过，代码只访问本地夹具，结束后无本实验浏览器残留。
- 有一份源单元格 9/18/19 与本地验证的对应说明，记录所有未执行变体。
- 云端扩展如未获授权，标为“未运行”，不能填假房源、截图、费用或耗时。

**演练状态：待演练。** 接收方记录实际日期、PowerShell/Python/浏览器包版本、退出码、断言结果及费用范围；本手册不包含已观测运行结果。下一模块见[可扩展部署概念](16-concepts.zh-CN.md)。
