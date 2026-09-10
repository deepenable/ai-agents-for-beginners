# 离线验证工具收据与一次性人工授权

## 学习目标

在只使用教学密钥和模拟动作的环境中，签署并验证收据，复核三份固定夹具，检测链中篡改，再运行人工授权的全部正反例。你还将证明几个重要的“不保证”：嵌入公钥不是组织身份，链前缀不能发现截尾，模拟 `execute` 不是实际退款。

## 准备、费用与破坏性操作警告

先阅读[环境准备](00-setup.zh-CN.md)和[收据信任边界](18-concepts.zh-CN.md)。使用 Windows、PowerShell 7、Python 3.12+；以下命令从固定源码仓库根目录运行。

**主线无需任何模型或云资源。** 安装阶段需要网络获取包；安装后密码学检查可在离线运行。不要运行浏览器、登录 Azure、申请管理员凭据或部署资源。不得导入真实私钥、生产收据或实际支付参数。源码生成器会覆盖它所在目录的三个 JSON 文件，因此本章只在复制后的练习目录执行它。

### 路线选择：已有课程环境或仅收据环境

已有环境的依赖遵循[根 requirements](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/requirements.txt)，不必重复安装 Agent Framework。

仅学习本模块时使用独立虚拟环境和[模块 requirements](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/requirements.txt)：

```powershell
py -3.12 -m venv .venv-receipts
.\.venv-receipts\Scripts\python.exe -m pip install -r .\18-securing-ai-agents\code_samples\requirements.txt
.\.venv-receipts\Scripts\python.exe -m pip check
New-Item -ItemType Directory -Force -Path .\lab-work\18-receipts | Out-Null
```

该文件要求 `pynacl>=1.5.0`、`jcs>=0.2.1`、`ipykernel>=6.0.0`，足以覆盖本模块，包括人工授权 notebook；不需要 `azure-identity`、Foundry、浏览器包或大模型权重。它是最低版本约束，不是精确锁。记录实际版本，不填写未经测试的“推荐版本”。

后文 `$Python` 指选中的解释器：

```powershell
$Python = (Resolve-Path .\.venv-receipts\Scripts\python.exe).Path
& $Python -m pip show pynacl jcs ipykernel
```

已有课程环境可将 `$Python` 改为其 Python 的明确路径。不会读取 `.env` 或打印任何秘密。

## 步骤一：识别两个 notebook 与三个夹具

阅读[基础 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/18-signed-receipts.ipynb)、[人工授权 notebook](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/human-authorization-receipts.ipynb)及[夹具说明](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/sample_receipts/README.md)。

固定版本的[模块 README](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/README.md)对应上述两份 Python notebook，没有 .NET notebook。基础文件覆盖签名、篡改、链和同步工具包装；后续文件覆盖精确动作审批与独立密钥权威。两者都列入本章演练，不能以只完成单张收据验签代替人工授权覆盖。本模块无需创建 `.env` 或保留任何云端可选占位配置。

| 文件 | 验证目标 |
| --- | --- |
| [01_valid_receipt.json](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/sample_receipts/01_valid_receipt.json) | 合法 lookup_flights 收据应为 True |
| [02_tampered_receipt.json](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/sample_receipts/02_tampered_receipt.json) | 修改 policy_id 后应为 False |
| [03_chain_three_receipts.json](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/sample_receipts/03_chain_three_receipts.json) | 三张签名、前驱连接和序号都有效 |

本文单元格编号是 JSON `cells` 的零基下标，包含 Markdown。不能将两个 notebook 的全局定义放入同一 namespace 后继续沿用：它们有同名 `sign_receipt`、`verify_chain`，参数与信任模型不同。

## 步骤二：执行基础收据的四段练习

将下面脚本保存为 `lab-work\18-receipts\receipt_checks.py`。只执行已审阅的固定基础 notebook 的明确代码单元格，跳过安装单元格 2；这不是用于未知 notebook 的通用安全执行器。

```python
import copy
import json
from pathlib import Path

source = Path(r"18-securing-ai-agents\code_samples\18-signed-receipts.ipynb")
nb = json.loads(source.read_text(encoding="utf-8"))
scope = {}
cells = (3, 5, 7, 9, 11, 13, 16, 19, 20, 21, 23, 26, 27)
for index in cells:
    code = "".join(nb["cells"][index]["source"])
    exec(compile(code, f"{source}:cell-{index}", "exec"), scope)

verify = scope["verify_receipt"]
verify_chain = scope["verify_chain"]
assert verify(scope["receipt"]) is True
assert verify(scope["prehashed_receipt"]) is False
assert verify(scope["tampered"]) is False
assert all(r["overall_valid"] for r in verify_chain(scope["chain"]))

bad = verify_chain(scope["tampered_chain"])
assert bad[0]["overall_valid"]
assert not bad[1]["signature_valid"]
assert bad[2]["signature_valid"] and not bad[2]["chain_link_valid"]
wrapped = scope["receipted_lookup"].receipts
assert len(wrapped) == 3
assert all(r["overall_valid"] for r in verify_chain(wrapped))

fixtures = Path(r"18-securing-ai-agents\code_samples\sample_receipts")
valid = json.loads((fixtures / "01_valid_receipt.json").read_text(encoding="utf-8"))
tampered = json.loads((fixtures / "02_tampered_receipt.json").read_text(encoding="utf-8"))
chain = json.loads((fixtures / "03_chain_three_receipts.json").read_text(encoding="utf-8"))
assert verify(valid) is True
assert verify(tampered) is False
assert len(chain) == 3 and all(r["overall_valid"] for r in verify_chain(chain))
assert any(not r["overall_valid"] for r in verify_chain([chain[0], chain[2]]))
assert any(not r["overall_valid"] for r in verify_chain([chain[1], chain[0], chain[2]]))
assert all(r["overall_valid"] for r in verify_chain(chain[:2]))
print("BASIC PASS: direct JCS, tamper, chain, wrapper and fixtures")
print("BOUNDARY: a valid prefix passes without an external expected head")
```

执行：

```powershell
& $Python .\lab-work\18-receipts\receipt_checks.py
```

预期结果与解释：

1. 单元格 7 在内存随机生成 Ed25519 密钥，公开输出只有公钥。每次运行的公钥/签名可能不同，不抄固定输出作为通过标准。
2. 单元格 11 直接签 JCS payload；13 的正常收据 True、预哈希负例 False。若两者都 True，检查是否错误修改了验签输入。
3. 单元格 16 改的是 `policy_id`，不是实际执行任何政策变更；验签应失败。
4. 单元格 23 篡改中间记录的参数哈希，应导致第 1 张签名失败、第 2 张连接失败，但第 2 张自己的签名仍通过。
5. 单元格 26–27 的 `ReceiptedTool` 包装 mock flight lookup，三次调用得到三张相连收据；没有航班查询网络请求，也没有占座/订票。
6. 三个固定夹具与内存新生成的收据不同，不能按整份 JSON 相等判断；应按密码学验证与链规则判定。

脚本最后的前缀断言故意通过，用来证明“没有可信最终链头时，不能发现被隐瞒的尾部”。这不是需要通过修改签名算法修复的问题。

## 步骤三：在副本中验证可复现夹具生成

先阅读[generate_fixtures.py](https://github.com/deepenable/ai-agents-for-beginners/blob/25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595/18-securing-ai-agents/code_samples/sample_receipts/generate_fixtures.py)。它使用公开的固定测试密钥和固定时间戳，输出位置由 `Path(__file__).parent` 决定；**这些密钥不是秘密，更不是生产凭据**，不要把测试钥匙当组织信任根。

复制并只在副本运行，命令将覆盖目标练习目录中同名的三份文件：

```powershell
$SourceFixtures = '.\18-securing-ai-agents\code_samples\sample_receipts'
$FixtureCopy = '.\lab-work\18-receipts\fixtures'
New-Item -ItemType Directory -Force -Path $FixtureCopy | Out-Null
Copy-Item -LiteralPath "$SourceFixtures\generate_fixtures.py" -Destination $FixtureCopy
& $Python "$FixtureCopy\generate_fixtures.py"
```

随后按对象相等验证，避免 Windows 换行格式把字节比较变成平台差异：

```powershell
@'
import json
from pathlib import Path
src = Path(r"18-securing-ai-agents\code_samples\sample_receipts")
dst = Path(r"lab-work\18-receipts\fixtures")
for name in ("01_valid_receipt.json", "02_tampered_receipt.json", "03_chain_three_receipts.json"):
    assert json.loads((src / name).read_text(encoding="utf-8")) == json.loads(
        (dst / name).read_text(encoding="utf-8")
    ), name
print("FIXTURES PASS: parsed content matches the pinned source")
'@ | & $Python -
```

固定生成器适合回归夹具，不适合生产收据签署。正式字节兼容验证应以双方约定的规范字节或测试向量为准，不将文件换行等同于 JCS 签名消息。

## 步骤四：执行人工授权全部反例

在独立脚本 `lab-work\18-receipts\approval_checks.py` 保存以下内容。重新创建 namespace，使两种收据验证器互不覆盖。直接使用源虚构动作，不连接任何实际收款账号。

```python
import json
from pathlib import Path

source = Path(
    r"18-securing-ai-agents\code_samples\human-authorization-receipts.ipynb"
)
nb = json.loads(source.read_text(encoding="utf-8"))
scope = {}
for index in (1, 3, 5, 6, 8, 10):
    exec(compile("".join(nb["cells"][index]["source"]),
                 f"{source}:cell-{index}", "exec"), scope)

verify = scope["verify_chain"]
make_approval = scope["human_approval"]
make_receipt = scope["agent_receipt"]
action = scope["action"]
now = "2026-07-08T15:06:00Z"
approval = make_approval(
    action, "training-approver", now, expires_at="2026-07-08T15:16:00Z"
)
receipt = make_receipt(action, approval, now)
ok, why = verify(action, approval, receipt, now)
assert ok, why
ok, why = verify(action, approval, receipt, now)
assert not ok and "consumed" in why

changed = {**action, "params": {**action["params"], "amount_usd": 1}}
ok, why = verify(changed, approval, make_receipt(changed, approval, now), now)
assert not ok and "digest substitution" in why
print("APPROVAL PASS: fresh binding accepted, replay and changed action refused")
```

执行：

```powershell
& $Python .\lab-work\18-receipts\approval_checks.py
```

日期是源夹具中的**模拟时钟**，不是现实当前时间，也不是实际批准日期。不要换成今天后对既定过期案例作错误解释。所有正反例都只在内存模拟状态中运行。

源单元格 10 按 13 组问题组织，实际会打印 14 条拒绝结果（malformed 组含审批和代理两条）。接收方逐项记录如下结果；如某项意外成功或异常崩溃，该项不通过：

| 输出标签 | 预期拒绝类别 |
| --- | --- |
| `tamper`、`confused-deputy` | 批准绑定的动作与当前动作不同，摘要替换 |
| `replay` | 批准已消费 |
| `forged-approval` | 攻击者密钥冒用可信审批 key ID，签名不符 |
| `self-minted-agent` | 自制代理密钥不匹配可信代理公钥 |
| `wrong-action-agent` | 代理收据绑定不同动作 |
| `malformed-approval`、`malformed-agent` | 收据结构缺失 |
| `wrong-len-sig` | 签名长度不合法，拒绝而不是崩溃 |
| `nonobject-receipt` | list 不是合法收据对象 |
| `stale-policy` | 当前策略已变，旧批准不再授权 |
| `stale-key` | key ID 已不在审批人固定注册表 |
| `expired-approval` | 到执行时批准已过期 |
| `digest-substitution` | 指向真实批准，但该批准是另一个动作 |

以上是待观察的预期类别。只看到最后一条 `APPROVAL PASS` 不等于已经检查源输出的所有拒绝；应把 14 条分别对应表格，不能丢掉中间结果。

## 步骤五：把输出转化为可检验的边界

做三个进一步的本地检查，每次使用新的教学批准或新 namespace，避免上一个成功调用已经消费批准干扰结论：

1. **不依赖自报钥匙。** 对照基础 `verify_receipt` 使用 `signature.public_key` 与人工授权 `verify_envelope` 使用注册表。解释为什么后者不能随收据提交任意公钥获得权限。
2. **恢复不等于防重放持久化。** 新进程中 `_consumed` 重新为空；说明实际系统必须持久、原子地登记消费，不能通过进程内集合宣称全局 exactly-once。
3. **授权与效果分离。** 查看 `execute`，确认它只返回布尔值和字符串。把验收语句写成“绑定检查接受模拟动作”，而不是“人类完成真实 WebAuthn 审批，退款已到账”。

针对时间，指出代码只把 `now` 与 `expires_at` 作统一格式字符串比较；生产需校验格式、时钟、签发/执行窗口及异常字段。针对政策，`policy_version` 相等只说明版本绑定，不证明政策评估的实际过程。

## 步骤六：有意义的扩展路线

### 新字段与内容承诺

在基础 notebook 的练习副本给 `make_receipt` 的 payload 增加 `request_id`，**在签名前加入**。合格条件：正常验签 True，签后只改该字段则 False。仅改 signature 对象里的展示元数据并不等同于修改已签 payload。

再按固定顺序拼接两张收据的规范字节并计算 SHA-256，把摘要放入第三张收据 payload 后签名。验证交换前两张顺序会改变摘要。说明这只是对两份内容的承诺；完整选择性披露还需要结构化证明路径与协议定义，不能把它当作已实现标准 Merkle 审计。

### 框架集成与失败收据

基础 notebook 单元格 28 只有 Microsoft Agent Framework 伪代码草图，不是已经跑通的集成；主线无需安装模型 SDK。若接收方另行批准框架扩展，必须让代理注册包装后的工具，明确异步/同步签名、参数序列化和错误返回。

先只包装本地模拟函数：成功一次产生一张收据，抛异常一次应产生**专门设计的失败收据**或明确记录当前 wrapper 没有覆盖。源 `ReceiptedTool` 只在正常返回后签名，不能声称已有异常审计。多工具调用若需要一条全局链，应改用共享的顺序存储，而不是各自的 `receipts` 列表。

### 生产治理设计作业

无需部署，提交以下决策：谁认证公钥归属、如何保护/轮换私钥、如何发布撤销信息、如何原子消费批准、如何保留不可变链与可信链头、如何最小化包含完整 action 的批准记录。每项给一个失败场景和检测证据。

如果要采用外部收据库或第三方向量，先确认 wire format、算法、签名范围与许可证；本课教学平铺格式不声称符合某个 Internet-Draft 的完整 envelope。后量子迁移需要实际算法与双签验证实现，不能只改 `alg` 字符串。

## 故障排查

| 现象 | 检查顺序 |
| --- | --- |
| `nacl`/`jcs` 缺失 | 确认 `$Python` 指向安装本模块 requirements 的环境 |
| 合法固定夹具验签失败 | 使用固定英文源码，先排查多余预哈希、signature 范围与 base64url 补位 |
| 所有签名通过但身份不可信 | 基础验证器只信收据自带公钥；使用独立固定注册表核查权限 |
| 第二次正常运行被判重放 | 同一 namespace 内批准已消费，这是预期；用新的教学批准 |
| 过期案例与系统日期不符 | 使用给定模拟 `NOW`，不要把夹具时间当实际审批 |
| 重生成修改源 JSON | 停止操作，确认运行的是练习目录副本；不要在源目录再次执行 |
| 对任意畸形字段仍可能异常 | 当前样例不是完备 schema 防线；记录局限，勿宣称所有不可信输入都已验证 |

## 清理与精确通过标准

关闭运行脚本/kernel，丢弃内存教学私钥；不要保存或发布 private key/seed。保留脱敏的断言结果即可。确认目录只含本次练习副本，再预览删除：

```powershell
Remove-Item -LiteralPath .\lab-work\18-receipts -Recurse -WhatIf
```

确认后去掉 `-WhatIf`。仅收据虚拟环境如不再使用，可对 `.venv-receipts` 单独预览后删除；不要删除共享课程环境、原始夹具或真实审计数据。

完成标准：

- 正常直接 JCS 收据通过，预哈希与篡改收据拒绝。
- 三张正常链通过，中间篡改时签名/链连接失败层符合预期。
- 包装 mock 工具三次调用产生三张合法收据；固定生成器副本对象内容与源夹具一致。
- 人工授权正例与 14 条拒绝结果逐项核查，额外重放/变更动作断言通过。
- 能准确说明身份、可信时间、实际执行、截尾检测和跨进程一次性保证尚需哪些系统。

**演练状态：待演练。** 本次交付只提供内容与可执行步骤，没有签名运行、模型或生产业务观测结果。接收方应记录实际日期、Python/依赖版本、每组断言和未解决问题；预期输出不得代替演练记录。
