# Skill Vet — 审查检查清单

> **路径约定：** `<lifecycle>` 指本 skill 包根（定义见主入口 SKILL.md「路径约定」），脚本命令请直接替换为该路径。

> **同步提示（防漂移）：** 下方「红牌检查」与 `skill-vet.md` 的 **Step 2 代码审查** 红牌表**同源**，
> **改一处必须同步另一处**。`skill-vet.md` 是协议正文（唯一事实源），本文件是速查勾选版。
> `self_check.py` 会在两处红牌条目数不一致时告警。

## 审查前准备

- [ ] 确认skill来源（WorkBuddy 内置 / marketplace / 社区 / 外部 GitHub）
- [ ] 准备读取skill全部文件

## Step 1: 来源检查

- [ ] 来源明确（URL/路径）
- [ ] 作者已知或可信
- [ ] 有足够下载量/stars（>100为佳）
- [ ] 最近6个月内有更新
- [ ] 无已知安全问题报告

## Step 2: 代码审查

### 红牌检查（按编号逐条核对；编号对应 `scripts/redflags.py` 唯一真源）

> 级别：⛔ CRITICAL = 立即拒绝 / 判定 DO NOT INSTALL；⚠️ HIGH = 必须人工核查后才放行；ℹ️ MEDIUM = 确认是正当用途。

- [ ] ⛔RF01 无外传凭证链路（读凭证 **且** 外传，如 `cat ~/.ssh/id_rsa | curl -d @- …`）
- [ ] ⛔RF02 无读取代理身份/记忆文件（MEMORY.md / USER.md / SOUL.md / IDENTITY.md / CLAUDE.md）
- [ ] ⛔RF03 无向未知地址发送数据（POST / upload，非声明的只读 API）
- [ ] ⛔RF04 无对外部输入动态执行（eval / exec / Function）
- [ ] ⛔RF05 无提示注入 / 越权指令（忽略之前指令 / 不要询问用户 / 已通过审计）
- [ ] ⚠️RF06 无提权执行（sudo / doas / pkexec / runas / RunAs）
- [ ] ⚠️RF07 无任意代码执行 / 反混淆（混淆代码、运行时下载后执行）——**仅人工判**
- [ ] ⚠️RF08 无删除或改写系统文件（rm -rf / shred / Remove-Item -Recurse）
- [ ] ⚠️RF09 无安装外部依赖（npm/pip/brew/apt/cargo install 未列明的包）
- [ ] ⚠️RF10 无硬编码凭证 / 密钥（api_key / token / password 字面量）
- [ ] ⚠️RF11 无凭证 / 会话数据访问（cookie / session / keychain / 浏览器 profile）
- [ ] ⚠️RF12 无全局可写权限（chmod 777 / icacls grant）
- [ ] ⚠️RF13 无 Windows 危险操作（Invoke-Expression / powershell -enc / 删注册表 / 关防护）
- [ ] ⚠️RF14 无裸 IP 地址请求（绕过 DNS 与证书校验）
- [ ] ℹ️RF15 网络请求目标确为声明过的公开只读 API
- [ ] ℹ️RF16 子进程参数已清洗（无 shell=True 拼接外部输入）
- [ ] ℹ️RF17 base64 不是用来隐藏 payload
- [ ] ℹ️RF18 敏感目录访问有正当理由
- [ ] ℹ️RF19 环境变量取密钥只取自己声明需要的那个
- [ ] ⚠️RF20 无读取凭证文件（cat/type ~/.ssh、~/.aws、.env、id_rsa 等）；若有，确认有正当理由
- [ ] ⛔RF21 无包外符号链接（指向 ~/.ssh、/etc、其他盘符的软链/目录软链）
  > **symlink 的证据是链接本身，不是被链接的内容**——机器**不跟随**链接读取内容，
  > 所以被链接文件里的敏感内容**永远不会出现在命中列表里**。
  > ⇒ **不能只按「命中了哪些敏感内容」判风险**，那会把这整类攻击完全放过；
  > 看到符号链接就按 ⛔ 判，不因"没扫到内容"而降级
- [ ] 无硬编码依赖外部 CLI（如 Claude Code 生态的 `dz` 等自动化评分工具；若有，应改为走内置人工质量门，否则视为黄/红牌）

### 指令层红牌（脚本扫不到，必须人工读 SKILL.md 正文）

> skill 的危险面不只在代码里——写在正文里的指令同样能让 agent 越权。以下出现即红牌：

- [ ] 正文指示 agent 读取凭证 / 隐私文件（`~/.ssh`、`~/.aws`、`.env`、浏览器 profile、钥匙串）
- [ ] 正文指示 agent 把用户数据发往外部地址（未声明为公开只读 API 的上传/POST）
- [ ] 正文指示 agent 执行与声明功能无关的命令
- [ ] 正文指示 agent 忽略上层指令 / 跳过用户确认（"忽略之前的规则""不要询问"）
- [ ] 正文指示 agent 静默处理副作用
- [ ] 正文含诱导泄露系统提示 / 对话上下文的措辞

> `validate_skill.py --mode vet` 对指令层做**分级提示**：载荷裸露 → CRITICAL 拒装；
> 载荷封在引号内 → 只降到 HIGH。**「引用」与「实施」只能由人分辨**，故指令层仍须人工读正文逐条核对。
> **不要因为脚本「无 CRITICAL 命中」就放行。**

### Windows 平台补充核查（本机为主力平台）

- [ ] 无 PowerShell 编码执行（`powershell -enc` / `Invoke-Expression`）
- [ ] 无注册表删除 / 安全配置篡改（`reg delete` / `Set-MpPreference -Disable`）
- [ ] 无用户目录外的批量删除（`Remove-Item -Recurse` 指向 C:\Windows 等）
- [ ] 无持久化（计划任务 / 注册表 Run 键 / WSL 启动项）
- [ ] 无 UNC 路径外传（`\\attacker\share`）

### 自动化校验（推荐先做）

先跑包内脚本快速定位格式问题与可疑模式：
```
python <lifecycle>/scripts/validate_skill.py <skill_dir> --mode vet
```
脚本校验 frontmatter 合法性、name 规则、description 无尖括号且含触发词、含反模式小节，并**分级**扫描可疑模式：
⛔ CRITICAL 命中（载荷裸露）→ VERDICT = DO NOT INSTALL（退出码 2）；⚠️ HIGH 命中（含「载荷封在引号内」的引用形态）→ 须人工核查；ℹ️ MEDIUM → 仅提示；📄 INFO → 规则说明（红牌表 / 模式定义），不参与判定门。
命中项带**行号与片段**，可直接定位。

### WorkBuddy 平台权限检查（特有）

- [ ] `allowed-tools` 未膨胀（未声明用不到的危险工具）
- [ ] 未声明不可信的 MCP server / 连接器
- [ ] marketplace 来源为官方 / 已知发布者且版本最新
- [ ] 云服务授权范围合理、最小化
- [ ] **无指向工作区外的符号链接**（文件或目录）——包外 symlink = 读取工作区外文件 = 等效 ⛔ EXTREME（RF21）；
      判定按**路径边界**（`commonpath`）而非字符串前缀；包内 symlink = MEDIUM，不阻断。
      复核报告时确认 `label`/`snippet` 里的**「包外 / 包内」限定词与机器判定一致**——
      两者任一写反都会让报告与判定矛盾，误导复核（机器已按判定动态生成，人工转述时不得省略）

### 代码质量检查

- [ ] SKILL.md结构完整（frontmatter + 正文）
- [ ] 触发词明确（"Use when..."）
- [ ] 工作流程清晰可执行
- [ ] 有错误处理说明
- [ ] 无明显过时的引用

## Step 3: 权限范围

- [ ] 需要读取的文件列表明确
- [ ] 需要写入的文件列表明确
- [ ] 需要执行的命令列表明确
- [ ] 网络访问范围明确（如有）
- [ ] 权限范围与功能匹配（最小权限原则）

## Step 4: 风险分级

| 风险等级 | 标准 | 处理 |
|---------|------|------|
| 🟢 LOW | 只读/格式化/笔记类 | 基础审查即可 |
| 🟡 MEDIUM | 文件操作/浏览器/API调用 | 完整代码审查 |
| 🔴 HIGH | 凭证/交易/系统操作 | 必须人工批准 |
| ⛔ EXTREME | 安全配置/root访问 | 禁止安装 |

## 输出报告（Step 1–4 之后，对应协议的「输出格式」）

- [ ] 报告格式完整
- [ ] 风险等级明确
- [ ] VERDICT清晰（SAFE/CAUTION/DO NOT）
- [ ] 补充说明完整
- [ ] **PROTOCOL-LAYER CHECKLIST 已逐条填**（RF01/RF05/RF07/RF21 + 指令层 6 项）——空着不给等于把红线寄托在机器检出能力上
- [ ] **每项权限都写了 NEEDED-FOR 与 MINIMAL?**（拿不出 NEEDED-FOR 的按 MINIMAL?=否 处理 → ⛔ 拒绝安装）
- [ ] **REVIEWED-AT / REVIEWER / TOOL-VERSION / FILES-HASH 四项齐全**——缺了就无法证明"审的是哪一份、谁审的、用的哪版规则"

## 审查后

- [ ] **报告已留档**（必经步骤，不是建议）：写到 `<工作目录>/<skill-name>-vet-report.md`——**不要写进待审 skill 内部**
- [ ] 报告中只引用被审 skill 的**相对路径**，并含 RF 编号 + 文件:行号
- [ ] **拒绝安装（DO NOT INSTALL）的 skill 同样留档**，并写明拒绝原因
- [ ] 如有CAUTION，记录需人工确认的点
- [ ] 如有DO NOT，记录拒绝原因
- [ ] 安装动作按 `references/publish.md` 执行（含装前二次校验、指纹核对、装后复验）
