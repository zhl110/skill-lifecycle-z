# Skill Create — 创建新 Skill（参考协议，按需读取）

两种模式：**CAPTURED**（从执行痕迹提取）和 **DERIVED**（合并现有 skill）。

> **路径约定：** `<lifecycle>` 指本 skill 包根（定义见主入口 SKILL.md「路径约定」），下文脚本命令请直接替换为该路径。

本协议的工艺对齐 WorkBuddy 内置 `skill-creator` 的方法论：先挖掘可复用内核，再规划要打包的资源，再写，最后用脚本自动校验。lifecycle 额外保留了自己的治理长板：CHECKPOINT 确认纪律、反模式表、eval 强制、DERIVED 合并。

---

## 总览：从"想法/痕迹"到"可用的 skill"

```
1. 挖掘内核   — 痕迹模糊时先向用户澄清可复用内核（Step 0）
2. 规划资源   — 决定要不要带 scripts/references/assets（资源规划）
3. 写 SKILL.md — frontmatter + 触发描述 + 结构化步骤 + 反模式 + ≥2 eval
4. 自动化校验 — python <lifecycle>/scripts/validate_skill.py <目录>（硬门）+ 人工兜底
5. CHECKPOINT — CP-C1/CP-C2/CP-C3 关键节点等用户确认
```

**工艺原则（来自 skill-creator，必须遵循）：**
- 渐进披露：SKILL.md 保持精简（**目标 < 100 行，硬性上限 < 500 行**），细节按需拆到 `references/`；同一份信息不要既在 SKILL.md 又在 references 里重复。
- 写作风格：整篇用祈使句 / 不定式（动词开头），客观指令式语言，不用第二人称"你/your"。
- 自动化校验优先：造完一律跑 `validate_skill.py`，不靠"记得检查"。

---

## Step 0：挖掘可复用内核（痕迹模糊时必做）

CAPTURED 默认"执行痕迹已存在"，但现实中用户常含糊说"把刚才的任务总结成 skill"，痕迹是散的、甚至当时没记录。此时**不要凭空编造**，先向用户澄清内核：

**澄清的问题（一次别问太多，先问最关键的 1–3 个）：**
- 这个 skill 该支持哪些具体功能？（边界在哪，什么不算它的活）
- 给 2–3 个真实使用例子（最好用户会怎么触发它）
- 用户大概率会怎么说 / 输入什么来唤起它？（→ 提取触发词）
- 当时执行时踩过什么坑？（→ 反模式素材）

**问完再判定可复用性（值不值得造）：**
- 通用吗？未来类似任务能否受益？ → 不通用就拒绝创建（见反模式"过度特化"）
- 能参数化吗？把硬编码换成变量 / 参数
- 是不是只包装单个命令、不增值？ → 拒绝（见"过于琐碎"）

> 痕迹清晰（刚跑完一个可复现流程、工具调用序列明确）可跳过 Step 0，直接进入模式协议。

---

## Mode 1: CAPTURED — 从执行痕迹提取

**适用场景：** 一个任务成功执行完毕，其中的方法 / 流程可复用于未来类似任务。

### CAPTURED 协议

1. **（必要时）挖掘内核** — 痕迹模糊时走 Step 0 向用户澄清，拿到的内核即下方"识别模式"的输入。
2. **分析执行痕迹** — 用了哪些工具？什么顺序？做了哪些关键决策？
3. **识别可复用模式** — 这个模式是否通用？能否参数化？未来类似任务能否受益？
4. **规划要打包的资源** — 见下方「资源规划」，决定 SKILL.md 之外要不要带 `scripts/` `references/` `assets/`。
5. **提取元数据** — name、description（含触发词）、协议步骤、反模式。
6. **脚手架 + 填充 SKILL.md** — 按下方模板手写（frontmatter 含 `name` + `description` + `metadata.version`），写清楚触发条件和执行步骤；按「资源规划」决定要不要建 `scripts/` `references/`。
7. **自动化校验** — 跑 `python <lifecycle>/scripts/validate_skill.py <skill目录>`；未通过则按报告修，直到全绿。
8. **人工质量门（兜底）** — 脚本过了仍需逐项过下方「验证替代」清单。

### 资源规划（决定要不要带 scripts/references/assets/records）

**完整清单与逐项判据见 `references/create-templates.md` 的「标准 skill 结构：四档形态」**（配一张四档形态图）。
本节只留一条原则，避免两处各写一份表、迟早写岔：

> 只有 `SKILL.md` 与 `evals/basic.md` 是**必需**的。
> `references/` `scripts/` `assets/` `records/` 每一项都要有明确理由才加，理由写不出来就不加。
> 分目录看**读者**：agent 读的放 `references/` `scripts/` `evals/`，人读的放 `assets/` `records/`。

### 输出要求

创建的 skill 必须包含：
- 清晰的触发描述（什么时候该用、什么时候不该用，description 含触发词）
- 结构化执行步骤（每一步能被另一个 agent 独立执行，遵循「写作风格规则」）
- 至少 2 个 eval 场景（happy path + 边缘场景），放 `evals/basic.md`
- 反模式表（什么时候 NOT 使用这个 skill）

### CAPTURED 质量门

| 检查项 | 标准 |
|--------|------|
| skill 名称 | 描述性命名，非泛化（如 "starlight-scaffold" 而非 "task-1"）；`^[a-z0-9\u4e00-\u9fff-]+$`，禁头尾 / 连续连字符。⚠️ 若该 skill 之后要交给内置 `skill-creator` 打包，必须改用纯 ASCII 名（其校验器只接受 `^[a-z0-9-]+$`）；中文名仅 WorkBuddy 加载器接受 |
| 协议步骤 | 与实际执行一致，非凭空编造 |
| 反模式 | 至少 1 个来自真实痕迹的坑 |
| 自动化校验 | `python <lifecycle>/scripts/validate_skill.py <目录>` 全绿（硬门） |
| 人工兜底 | 脚本过了仍需逐项过下方「验证替代」清单 |

---

## Mode 2: DERIVED — 合并现有 Skill

**适用场景：** 2+ 个 skill 经常被串联使用，且这个组合本身是一个可复用的工作流。

### DERIVED 协议

1. **识别候选 skill** — 哪些 skill 经常一起出现？
2. **分析协议** — 各自步骤是什么？自然交接点在哪？
3. **定义复合协议** — 取各 skill 的哪些步骤？什么顺序？哪里并行？
4. **处理数据流** — skill A 的输出怎样变成 skill B 的输入？
5. **规划资源 + 脚手架复合 SKILL.md** — 按「资源规划」决定要不要带上源 skill 的 `scripts/` / `references/`；标注 `source_skills` 引用。
6. **自动化校验** — 跑 `python <lifecycle>/scripts/validate_skill.py <目录>`，全绿后再独立验证复合流程。

### DERIVED 质量门

| 检查项 | 标准 |
|--------|------|
| source_skills | 至少 2 个 |
| 复合协议 | 非简单拼接，有实际集成逻辑 |
| when-to-use | 与任一源 skill 有明确区分 |
| 自动化校验 | `python <lifecycle>/scripts/validate_skill.py <目录>` 全绿 |

---

## 形态变体：路由型 skill（只写入口，不搬内容）

**什么时候用这个形态**：项目里已经有完整素材（文档、脚本、数据），你要的只是一个
「让 agent 知道去哪找、按什么顺序读」的入口。把内容复制进来是净损失 ——
原件一改就要同步两份，而这份副本永远不会比原件新。

**它和 CAPTURED / DERIVED 不是同一个维度**：那两个说的是「素材从哪来」，
这个说的是「最终做多厚」。组合起来就是 `CAPTURED + 路由型`。
素材是项目文件的，走 CAPTURED 的路径（只是把「执行痕迹」理解成「项目沉淀」）。

### 仍然要过 create 硬门 —— 「只做一个路由层」躲不掉两样东西

| 硬门项 | 路由型也得有 | 为什么不是形式主义 |
|--------|------------|------------------|
| 反模式小节 | ✅ | 路由型的主要失败模式是**误触发** —— 说了句沾边的话就被拉进来 |
| `evals/basic.md` ≥2 场景 | ✅ | 必须含**至少 1 个反向场景**（不该触发时确实没触发） |

> 对路由型 skill，**反向测试比正向测试更重要**。
> 一个总是误触发的 skill，比没有 skill 更烦人。

### SKILL.md 只写四样

1. **触发条件**（description + When to Use）—— 用户会怎么问，才该进来
2. **路由表** —— 什么情况读哪个文件，写清稳定路径
3. **执行顺序** —— 先读什么、再读什么、哪一步不能跳
4. **反模式** —— 什么时候**不该**用这个 skill

**不写**：具体做法、领域知识、案例细节。那些在项目文件里，重抄一遍等于给自己埋同步债。

### ⚠️ 包外引用：放法决定它能不能搬家

路由型 skill 必然引用包外文件。放哪里，后果完全不同：

| skill 放哪 | 引用写法 | 结果 |
|-----------|---------|------|
| **项目内**（项目下的 `.workbuddy/skills/`） | 相对路径 `../docs/a.md` | ✅ 跟着项目走，换机器也好用 |
| **用户级**（`~/.workbuddy/skills/`） | 相对路径 | ❌ **装到别处即断**：`../docs/` 指向完全不同的地方 |
| **用户级** | 绝对路径 `D:\proj\docs\a.md` | ⚠️ 本机可用，换机器 / 换盘符即废 |

> ⚠️ **这一项 `self_check.py` 查不到**：它的交叉引用检查只覆盖包内的
> `references/` `scripts/` `assets/` `records/`，`../` 开头的路径不在范围内。
> 所以**不会报错，但装完就废**。选放法时自己确认。

**建议**：能给项目用就放项目内。真要放用户级，就在 SKILL.md 顶部写一行
「本 skill 依赖 `<绝对路径>`，换机器需改这里」—— 把隐性依赖变成显性。

### 额外自查（越过通用硬门之后）

- [ ] 路由表里每个路径都真实存在（手动点一遍，别信记忆）
- [ ] 反向场景真跑过：说一句沾边但无关的话，确认没被触发
- [ ] 没有把项目文件的内容抄进 SKILL.md

---

## 通用要求

所有创建的 skill 必须包含：

```markdown
---
name: <skill-name>
description: <一句话描述 + 触发词>
metadata:
  version: "0.1.0"
  status: "draft"
---

# <Skill Title>

## When to Use
- 触发场景 A
- 触发场景 B

## When NOT to Use
- 不应触发的场景

## Protocol
1. Step one
2. Step two
...

## Anti-Patterns
| 反模式 | 检测方式 | 修复方案 |
|--------|---------|---------|
| ... | ... | ... |
```

> Description 写法、SKILL.md 模板、何时加脚本 / 拆文件、Review Checklist 详见 `references/create-templates.md`。

**必须同时创建 `evals/basic.md`（≥ 2 个测试场景：happy path + 边缘场景）** —— 这是 `validate_skill.py`（create 模式）的硬门，缺了校验会直接失败。模板外的目录结构：

```text
<skill-name>/
├── SKILL.md          # 上方模板（frontmatter 含 name + description + metadata.version）
└── evals/
    └── basic.md      # 至少 2 个测试场景（用 ## 标题分隔）
```

`evals/basic.md` 最小示例（**标题必须含「场景」二字**，校验器按场景标题或「输入+预期」条目计数，任意标题不算场景）：

```markdown
## 场景1：核心 happy path
输入：<一个典型触发>
预期：<期望输出>

## 场景2：边缘场景
输入：<含糊 / 不规范输入>
预期：<期望输出>
```

---

## 写作风格规则（必须遵循）

写新 skill 的 SKILL.md 时，整篇遵守：

- **祈使句 / 不定式**：步骤用动词开头（"用 X 转 Markdown"、"检查输出"），不用 "you should / 你应该"。
- **客观指令式**：直接说动作，不夹主观评价；不用第二人称"你 / your"。
- **每步一个动作**：可让另一个 agent 独立执行，不依赖未写明的上下文。
- **术语一致**：同一概念全文同一词，不中途换名。
- **具体示例**：复杂步骤配一个最小可运行示例，不空泛。

---

## 反模式（创建时避免）

| 反模式 | 检测 | 修复 |
|--------|------|------|
| 过度特化 | skill 只适用于原始任务 | 泛化：用参数替换硬编码 |
| 过于琐碎 | 只包装单个命令，不增值 | 拒绝创建，不值得维护 |
| 重复 skill | 与现有 skill 重叠 80%+ | 合并到现有 skill 或创建 DERIVED |
| 缺反模式 | 无"NOT to use"指导 | 从失败分析中补充 |
| 未测试 | 无 eval 场景 | 至少 2 个场景再发布 |
| SKILL.md 臃肿 | 单文件 > 100 行且未拆 | 拆到 references/，遵循渐进披露 |

---

## 依赖与环境

> WorkBuddy 环境**没有** Claude Code 生态的 `dz` 等自动化 CLI。本 skill 一律走「手动脚手架 + 自动化校验脚本 + 人工质量门」，无需安装任何外部工具。

| 资源 | 用途 |
|------|------|
| 手动脚手架 | 在 `~/.workbuddy/skills/<name>/` 下按上方模板手写目录与 SKILL.md |
| 自动化校验脚本 | `<lifecycle>/scripts/validate_skill.py <目录>` —— 校验 name / description / 触发词 / eval / 反模式，硬门 |
| 人工质量门 | 下方核对清单，作为脚本兜底 |

---

## 实际示例

### 示例1：CAPTURED模式

**场景：** 用户刚完成了一个 PDF 转 HTML 的任务，想总结成 skill。

**输入：**
```
用户：刚做了个任务，帮我总结成skill
```

**执行过程：**
1. 痕迹清晰（markitdown→pandoc→自定义CSS），跳过 Step 0
2. 分析执行痕迹：用了 markitdown 转 md，pandoc 转 html，自定义 CSS
3. 识别可复用模式：PDF→MD→HTML 转换流水线
4. 资源规划：流水线固定，可放 `scripts/` 封装转换；本例先纯 SKILL.md
5. 提取元数据：name="pdf-to-html"，触发词="PDF转HTML"
6. 手动创建目录结构，填充 SKILL.md
7. 跑 `python <lifecycle>/scripts/validate_skill.py ~/.workbuddy/skills/pdf-to-html`，全绿
8. 人工质量门确认

**输出：**
```markdown
---
name: pdf-to-html
description: "PDF文档转HTML网页。Use when 用户提到'PDF转HTML'、'PDF做网页'。"
metadata:
  version: "0.1.0"
  status: "draft"
---

# PDF to HTML

## When to Use
- 将PDF文档转换为HTML网页
- 需要保留文档结构和格式

## When NOT to Use
- 扫描版PDF（需要OCR）
- 只需要提取纯文本

## Protocol
1. 用markitdown将PDF转为markdown
2. 用pandoc将markdown转为HTML
3. 应用自定义CSS样式
4. 输出自包含HTML文件

## Anti-Patterns
| 反模式 | 检测 | 修复 |
|--------|------|------|
| 直接用截图代替转换 | 输出是图片而非文本 | 使用OCR或文本提取 |
| 忽略PDF结构 | 表格/列表丢失 | 检查markitdown输出 |
```

---

### 示例2：DERIVED模式

**场景：** weather 和 forecast 两个 skill 经常一起使用，想合并。

**输入：**
```
用户：把weather和forecast合并成一个skill
```

**执行过程：**
1. 分析 weather skill：获取当前天气
2. 分析 forecast skill：获取天气预报
3. 识别交接点：都需要城市名输入
4. 定义复合协议：当前天气 + 预报一起返回
5. 资源规划 + 创建复合 SKILL.md（标注 source_skills）
6. 跑 `python <lifecycle>/scripts/validate_skill.py ~/.workbuddy/skills/weather-complete` 全绿

**输出：**
```markdown
---
name: weather-complete
description: "完整天气查询：当前天气+未来预报。Use when 用户提到'天气'、'weather'、'预报'。"
metadata:
  version: "0.1.0"
  status: "draft"
  source_skills:
    - weather
    - forecast
---

# Weather Complete

## When to Use
- 查询某城市的天气信息
- 需要当前天气和未来预报

## Protocol
1. 接收城市名输入
2. 并行获取当前天气和预报
3. 合并结果
4. 格式化输出

## Anti-Patterns
| 反模式 | 检测 | 修复 |
|--------|------|------|
| 只返回当前天气 | 未调用预报API | 确保两个API都调用 |
| 重复查询 | 同一城市查两次 | 缓存结果 |
```

---

## 🛑 CHECKPOINT：关键决策前确认

| # | 节点 | 触发条件 | 确认内容 |
|---|------|---------|---------|
| CP-C1 | 创建前 | 用户说"帮我创建skill" | 确认是 CAPTURED 还是 DERIVED 模式 |
| CP-C2 | 提取元数据后 | 完成痕迹分析 | 展示 name / description / 步骤，等用户确认 |
| CP-C3 | 创建完成后 | SKILL.md 填充 + 校验完成 | 展示创建的 skill，建议下一步（改进 / 审查） |

**违反 CHECKPOINT 的信号：** 如果你在没有用户确认的情况下直接创建了 skill，立即停下，回溯到 CP-C1。

---

## 异常处理

| 场景 | 一线修复 | 兜底 |
|------|---------|------|
| skill 名称已存在 | 询问用户：覆盖 / 重命名 / 取消 | 重命名时加后缀（如 pdf-to-html-v2） |
| 执行痕迹不清晰 | 走 Step 0 询问用户补充关键步骤 | 跳过模糊步骤，只提取确定的部分 |
| 无法判断可复用性 | 标记为 draft，后续再判断 | 告知用户"建议先试用再决定是否固化" |
| 自动化校验未通过 | 按 `validate_skill.py` 报告逐项修 | 修复后重跑直到全绿 |
| 创建后发现与现有 skill 重复 | 分析差异，判断是否合并 | 合并到现有 skill 或保留差异化部分 |

---

## 创建后下一步

创建完成后，建议用户：

| 下一步 | 说明 | 使用的子 skill |
|--------|------|--------------|
| 改进 skill | 创建的是初版，需要迭代打磨 | skill-improve |
| 审查 skill | 确认安全性后再安装 | skill-vet |
| 直接使用 | 如果是简单 skill，可直接用 | - |

**建议流程：** create → improve（迭代 2–3 轮） → vet → publish

---

## 版本管理

创建时的版本设置建议：

| 场景 | 版本号 | 说明 |
|------|--------|------|
| 首次创建 | 0.1.0 | 初版，标记为 draft |
| 经过改进 | 0.2.0+ | 功能迭代 |
| 稳定版 | 1.0.0 | 经过测试，可正式使用 |

**版本记录（写进 SKILL.md frontmatter 的 `metadata`）：**
```yaml
metadata:
  version: "0.1.0"
  status: "draft"
```

---

## 手动脚手架 + 自动化校验兜底

WorkBuddy 没有 `dz` 这类 CLI，因此：

### 脚手架替代（替代 `dz create-skill`）

手动创建 skill 目录结构：

```text
~/.workbuddy/skills/<skill-name>/
├── SKILL.md          # 按上方模板手写（frontmatter 含 name + description + metadata.version）
└── evals/
    └── basic.md      # 至少 2 个测试场景
```

若带了脚本 / 参考，按需再加 `scripts/` `references/` `assets/`。

### 验证（自动化校验兜底）

**主路径 — 自动化校验脚本：**
```bash
python <lifecycle>/scripts/validate_skill.py ~/.workbuddy/skills/<skill-name>
```
脚本硬校验：SKILL.md 存在、frontmatter 合法、name 规则、description 无尖括号且含触发词、evals/basic.md 存在且 ≥2 场景、含反模式小节。未通过则按报告修。

**兜底 — 人工质量门（脚本过了仍建议过一遍）：**

| 检查项 | 标准 | 不通过处理 |
|--------|------|-----------|
| Frontmatter | 有 name + description（含触发词）+ metadata.version | 补充后重检 |
| 协议可执行性 | 每一步都能被另一个 agent 独立执行 | 细化模糊步骤 |
| 反模式覆盖 | ≥1 个不应触发的场景 | 从痕迹中挖掘 |
| eval 场景 | ≥2 个（happy path + 边缘） | 补充 eval |
| 文件完整性 | SKILL.md + 合法 frontmatter + evals/basic.md 存在 | 补建缺失文件 |
| 写作风格 | 祈使句 / 客观指令式、无第二人称 | 重写主观表述 |
