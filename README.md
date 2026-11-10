<p align="center">
  <img src="assets/01.jpg" alt="四道门：前三道放行，第四道红灯落杆拦停" width="880">
</p>

<h1 align="center">Skill Lifecycle Z</h1>

<p align="center">
  <kbd>v2.1.0</kbd>　<kbd>MIT</kbd>　<kbd>Python 3.x</kbd>　<kbd>零依赖</kbd>　<kbd>21 条红牌</kbd>
</p>

<p align="center">
  Skill 全生命周期治理：创建 → 改进 → 审查 → 发布<br>
  <sub>不是"帮你写 skill"，是"保证写出来的 skill 能用、能信、能追溯"</sub>
</p>

---

## 它解决什么问题

写 skill 不难，难的是三件事：

| 问题 | 本 skill 的做法 |
|------|----------------|
| 做过的流程每次都要重讲一遍 | **CREATE**：从执行痕迹提取成 skill，或合并多个 skill |
| skill 能用但不好用，改了还怕改坏 | **IMPROVE**：5 步迭代 + 每轮 before/after，判据是"原有内容没被改坏" |
| 从网上下了个 skill，不知道能不能装 | **VET**：21 条分级红牌 + 判定门 + 内容指纹，**能明确说出"不许装"** |
| 审完之后装的过程又被换掉了 | **PUBLISH**：TOCTOU 指纹核对 + 装后复验 + 留档 |

四个阶段之间**不自动串联**——每个阶段结束都有 CHECKPOINT 停下等确认。一个阶段做完，不代表下一个阶段该做。

## 四阶段

```
CREATE ──CP5──▶ IMPROVE ──CP5──▶ VET ──CP4──▶ PUBLISH
  │                │              │              │
CP1              CP2 CP3        CP4           CP-P1 P2
模式确认       备份/每轮对比   装不装由人定    安装/留档确认
```

| 阶段 | 输入 | 输出 |
|------|------|------|
| **CREATE** | 执行痕迹 / 待合并 skill 列表 | `SKILL.md` + `evals/basic.md`（≥2 真实场景） |
| **IMPROVE** | 目标 skill + 具体问题 | 改进后的 `SKILL.md` + before/after 对比 |
| **VET** | 待审 skill 目录 + 来源信息 | 风险报告 + `VERDICT` + 人工待核清单 |
| **PUBLISH** | 审查通过且用户明确同意 | 装入目标目录 + 装后复验 + 留档 |

> 从零设计一个全新的 skill（既无痕迹、也无合并对象）不归这里，用 WorkBuddy 内置的 `skill-creator`。

## 一眼看懂它是怎么运转的

光看文字很难理解"门、脚本、红牌真源、测试网"是怎么咬合的。包内有两张交互图，分工不同：

```bash
<lifecycle>/assets/architecture.html   # 讲结构：分成哪几层、谁依赖谁
<lifecycle>/assets/workflow.html       # 讲走法：什么情况走哪条路、哪里会被拦下
```

**架构图**四个视图：运行路线 / 红牌矩阵 / 五层结构 / 判定门。
**路径图**一张纵览：入口判断 → 四阶段 → 三道出口（拒装 / 装上 / 随时可停），带终止分支。

两张图都能点节点看细则，单文件、离线可开。

## 审查阶段：21 条分级红牌

<p align="center">
  <img src="assets/02.jpg" alt="红牌矩阵" width="720">
</p>

红牌不是"提示一下"，是**判定门**——严重度直接决定退出码：

| 级别 | 条数 | 判定门 | 后果 |
|------|------|--------|------|
| **CRITICAL** | 6 | BLOCKING | `VERDICT = DO NOT INSTALL`，**退出码 2**，不可被"用户坚持要装"绕过 |
| **HIGH** | 10 | REVIEW | 须人工核查后才可放行 |
| **MEDIUM** | 5 | INFO | 仅提示，多为正当用途 |

其中 **RF07（反混淆）、RF21（包外符号链接）没有机器可检的模式**——机器检不出不等于不是红线，这两条只能靠人看。这是"协议层与机器层解耦"的直接理由。

### 拦截：不是所有东西都能进

<p align="center">
  <img src="assets/04.jpg" alt="细网截留：危险物被挡在外面" height="340">
</p>

`--mode vet` 做的是**分级提示，不是判决**。判定规则只有一条：

- 载荷**裸露**在正文里 → 是在对读者下命令 → **CRITICAL，拒装**
- 载荷**封在引号内** → 当作被引用的字符串 → 降到 **HIGH，必须人工看一眼**
- 结构豁免（红牌表行 / 模式定义 / 测试夹具）→ **INFO**，不参与判定门

加前缀（`好的，`、`现在`、`请执行：`）不改变它是命令；加引号只让它从"拒装"变成"必须有人看一眼"，**不会变成放行**。

> 一句话：`security_pass` 只表示"无 CRITICAL"，不等于通过。CI 请判 `verdict` 或 `review_hits`。

### 判定：盖章是唯一不可逆的动作

<p align="center">
  <img src="assets/05.jpg" alt="高速微距：印章压进磨砂玻璃" height="300">
</p>

判定与退出码严格一致，不允许"检出风险却返回成功"：

| 退出码 | 含义 |
|---|---|
| `0` | 通过（仍可能有 HIGH，即"须人工核查"） |
| `1` | 格式校验未通过 |
| `2` | 拒装（CRITICAL 命中）或参数错误 |
| `3` | 内容指纹（seal）不一致 —— 审查完到安装之间文件被换过，**整份审查结论作废** |

### 单一真源：一处定义，多处投影

<p align="center">
  <img src="assets/03.jpg" alt="一个冷白核心向下投出多道光束，金属台面上落满完全相同的红色环" width="720">
</p>

21 条红牌只在 `scripts/redflags.py` 定义一次。扫描器**直接读真源、不复制**；需要人工维护的副本只有三处：`skill-vet.md` 的协议正文、`vet-checklist.md` 的勾选项、架构图里的红牌矩阵。

`self_check.py` 按**编号集合全等**校验这三处——任一处多一条、少一条、写错总数，都会 FAIL。

> 这条规矩的来源：同一份语义在多个地方各写一遍，必然漂移。凡"同一语义出现在 ≥2 个表达点"，就要问是否同源投影。

## 快速开始

WorkBuddy 中注册（本机已用 symlink 指向源目录，免重复维护）：

```bash
ln -s /d/mycode/agent-hub/skills/skill-lifecycle-z ~/.workbuddy/skills/skill-lifecycle-z
```

注册后直接对话触发，无需斜杠命令：

```
"帮我把刚才的任务总结成 skill"        → CREATE
"这个 skill 效果不好，帮我改进"       → IMPROVE
"这个 skill 安不安全？帮我看看"       → VET
"帮我把审查通过的 skill 装上"         → PUBLISH
```

> **路径约定：** 文中 `<lifecycle>` 指本 skill 包根（本机注册在 `~/.workbuddy/skills/skill-lifecycle-z`），脚本命令请直接替换为该路径。脚本能自动穿透软链解析包根。

### 首次使用

```
1. 说一句人话：
   - "帮我创建一个skill" → CREATE
   - "这个skill效果不好" → IMPROVE
   - "这个skill安不安全" → VET

2. 按提示提供信息：
   - skill 路径或名称
   - 回答几个确认问题（每个 CHECKPOINT 都会停下来问你）

3. 检查输出：
   - CREATE  → 生成的 SKILL.md + evals/basic.md
   - IMPROVE → before/after 对比
   - VET     → 红黄绿分级报告 + VERDICT
```

### 最小可用示例

```
你：刚做了个任务，帮我总结成 skill
→ 分析执行痕迹，提取可复用模式，创建新 skill（CP1 会先问你：从痕迹提取还是合并？）

你：humanize-ai-text 这个 skill 效果不好
→ 读 skill、跑测试 prompt、提炼问题模式，针对性改 1-2 处，给 before/after

你：这个 skill 安不安全？帮我看看
→ 查来源、跑红牌扫描、读正文核指令层、给风险等级与安装建议
```

## 怎么算用对了（成功度量）

这个 skill 的价值不靠"感觉好用"判断，靠三条可自查的指标：

| 指标 | 达标线 | 怎么查 |
|------|--------|--------|
| **创建产物可直接用** | `validate_skill.py` 全绿 + `evals/basic.md` 有真实场景 | 跑一次脚本 |
| **改进有据可依** | 有 baseline 对比，目标是「目标模式命中数归零 + 新问题数为 0」 | 看 `baseline.md` |
| **审查无遗漏** | 红牌 / 指令层红牌逐条核对过，结论有 VERDICT | 看审查报告是否覆盖指令层 |

**反过来说，这三种情况说明它没起作用：**

- 生成的 skill 过不了自己的校验脚本
- 改进只有"看起来更好"，没有 baseline 对比
- 审查报告只有脚本命中项，没有人工核对指令层

## 版本号怎么升

skill 演进时按这个档位 bump `metadata.version`：

| 版本号 | 含义 | 示例 |
|--------|------|------|
| 0.1.0 | 初版创建 | 首次从痕迹提取 |
| 0.2.0 | 功能改进 | 添加新步骤 / 新模式 |
| 1.0.0 | 稳定版 | 经过 3 轮以上迭代，测试通过 |
| 1.1.0 | 小修复 | 修复边界条件 / 文档更新 |
| 2.0.0 | 重大重构 | 架构变化 / 职责重新划分 |

记录方式：frontmatter 的 `metadata.version` 记版本号；改进过程在**目标 skill 目录**维护 `evolution-log.md`（可选，不在本包内）；git commit message 标注版本变化。

## 校验脚本

```bash
# 创建后硬门（格式 + 触发词 + metadata.version + 反模式小节 + evals ≥2 真实场景）
python <lifecycle>/scripts/validate_skill.py <skill_dir>

# 改进后：只要求"原有内容没被改坏"，不强制补齐本来就没有的 evals
python <lifecycle>/scripts/validate_skill.py <skill_dir> --mode improve

# 审查外部 skill：红牌扫描，CRITICAL 即退出码 2
python <lifecycle>/scripts/validate_skill.py <skill_dir> --mode vet

# 内容指纹：审查时记录，安装前核对
python <lifecycle>/scripts/validate_skill.py <skill_dir> --seal
python <lifecycle>/scripts/validate_skill.py <skill_dir> --verify-seal <值>

# JSON 报告（可接 CI）
python <lifecycle>/scripts/validate_skill.py <skill_dir> --mode vet --json
```

三种模式的区别不是"严格程度"，而是**评判标准**：`create` 要求完整创作规范；`improve` 只要求没退化（否则改进一个老 skill 会被硬门直接卡死）；`vet` 把创作规范降为警告，专注安全。

## 自检

```bash
python <lifecycle>/scripts/self_check.py          # 人类可读
python <lifecycle>/scripts/self_check.py --json   # JSON
```

九项，全部针对"文档与实现会不会漂移"：

1. `SKILL.md` frontmatter 合法
2. 引用表文件齐全（**双向**：引用的都存在 + `references/` `evals/` `records/` `assets/` 下每个文件都被引用，防死件）
3. `test-prompts.json` 能否正确路由到子协议
4. 无 Claude Code 生态残留
5. `scripts/` 工具脚本齐全
6. **文档声明的脚本调用与实现一致**（会真的去调脚本、真的去看 `--help`，不是比对源码字符串）
7. 红牌清单**三处**投影编号集合全等（协议正文 / 速查勾选 / 架构图）
8. **两份同源检查清单逐条一致**（`skill-improve.md` 的思维检查清单 ↔ `improve-checklist.md` 的每轮自检）
9. 包内文档互相引用无悬空

> 第 6 项有个刻意的设计：探不出实现支持的 `--mode` 集合时**报错**，而不是跳过——跳过等于给出虚假的绿灯。

## 回归测试

```bash
python <lifecycle>/scripts/test_redflags_adversarial.py   # 编码 / 载体 / 注入 / symlink 对抗
python <lifecycle>/scripts/test_redflags_gaps.py          # 缺口守卫 + 反向防线
python <lifecycle>/scripts/test_validate_skill.py         # 三模式 / CLI 契约 / seal
```

**改动 `scripts/` 下任何脚本后必须先跑这三套。**

其中 `test_redflags_gaps.py` 的核心是**反向防线**：修误报时最容易顺手把真阳性一起改没，而当只有误报用例时，"误报减少"和"真阳性丢失"在测试结果上无法区分——反向防线是唯一能区分的手段。

> 具体用例数会随迭代变化，此处不写死，以实跑输出的 `Ran N tests` 为准。

## 目录结构

```
skill-lifecycle-z/
├── SKILL.md                      # 主入口（路由 + 决策树 + 四阶段流程 + CP1–CP5）
├── README.md                     # 本文件
├── CHANGELOG.md  LICENSE
├── test-prompts.json             # 触发场景定义（由 self_check 校验路由）
├── references/                   # 按需加载的协议（agent 读）
│   ├── skill-create.md           #   创建协议（CAPTURED / DERIVED）
│   ├── skill-improve.md          #   改进协议（标准路径 / FIX）
│   ├── skill-vet.md              #   审查协议（4 步 + 指令层红牌）
│   ├── publish.md                #   安装协议（TOCTOU / 复验 / 留档）
│   ├── create-templates.md  create-evals.md
│   └── improve-checklist.md  vet-checklist.md
├── scripts/
│   ├── validate_skill.py         # 三模式校验 + 红牌扫描 + seal
│   ├── self_check.py             # 九项包内自检
│   ├── redflags.py               # 21 条红牌单一真源
│   ├── _common.py                # 共享规则（frontmatter / 场景计数 / 扫描范围）
│   ├── _residues.py              # 残留模式表（独立成模块，消除自指豁免）
│   ├── _fixtures.py              # 恶意载荷夹具
│   └── test_*.py                 # 三套测试网
├── evals/basic.md                # 自身评测场景
├── records/                      # 历史留档（非协议，不参与路由）
└── assets/                       # 给人看的静态资源（agent 不读）
    ├── architecture.html         #   架构图（讲结构）
    ├── workflow.html             #   工作路径图（讲走法）
    ├── skill-anatomy.svg         #   四档形态图（讲标准结构）
    └── 01–05.jpg                 #   宣传素材
```

## 静态资源（assets/）

`assets/` 放的是**给人看的**东西，不是协议 —— agent 不需要读它们。内容全部来自 SKILL.md 与 `references/`，是同一批信息的视觉 / 历史再表达。

### 图示

| 文件 | 讲什么 | 什么时候用 |
|------|--------|-----------|
| `assets/architecture.html` | **结构**：四阶段路线 / 红牌矩阵 / 五层结构 / 判定门 | 第一次接触本 skill；或要向人解释「它分成哪几层、谁依赖谁」 |
| `assets/workflow.html` | **走法**：入口判断 → 四阶段 → 三道出口（拒装 / 装上 / 随时可停） | 有人问「这个情况该走哪条路」「什么情况下会被拒」 |
| `assets/skill-anatomy.svg` | **形态**：四档形态（纯文本 → +参考 → +脚本 → +工程化）＋「按谁读分目录」的判据 | 新建 skill 前判断「这次要做到哪一档」；或有人问「标准 skill 该有哪些文件」 |

> 前两张是交互式 HTML（点节点看细则），第三张是静态 SVG（矢量、可任意缩放、可直接嵌进 md）。

### 宣传素材

**统一风格**：炭黑底 + 冷白 + 唯一强调色信号红 `#E23B2E`，哑光金属 / 磨砂玻璃质感，左上体积光，浅景深。

| 文件 | 画面 | 建议用途 |
|------|------|---------|
| `assets/01.jpg` | 四道门框横跨传送带，前三道绿光放行，第四道红灯 + 落杆拦住一个黑色方块 | 封面 / 头图（16:9，左侧留白可压标题） |
| `assets/02.jpg` | 暗色检验舱内，多张红色半透明卡片排成密集网格，几张被斜光照亮 | 讲「21 条红牌」时配图 |
| `assets/03.jpg` | 冷白球体向下投出多道光束，金属台面上落满**完全相同的红色环** | 讲「单一真源 / 同源投影」时配图。**不要当封面**——台面占满宽度，没地方压字 |
| `assets/04.jpg` | 极细金属筛网上堆满被截留的碎石，粉尘飞溅 | 讲「拦截 / 拒装」时配图（竖版 3:4，下方干净网格可压字） |
| `assets/05.jpg` | 高速微距：重型印章压进磨砂玻璃，红色印泥飞溅凝固 | 讲「判定 / 驳回」时配图（全系列质感最强） |

> ⚠️ **图里没有任何文字，是故意的。** 生图模型写中文必糊，标题与说明一律后期叠。
> 配文禁区：① 04 说「拦截」不说「过滤」（画面只有挡住、没有筛出）；② 03 说「一个源、多处落点、落点完全一样」，**别宣称「精确一一对应」**（光束数与环数并不严格相等）。

## 适合谁用 / 不适合谁用

| 你的情况 | 用什么 |
|---------|--------|
| 有反复做的流程，想固化成 skill | ✅ CREATE（CAPTURED） |
| 有几个 skill 总是一起用，想合成一个 | ✅ CREATE（DERIVED） |
| 已有 skill 效果不稳，想找出根因改掉 | ✅ IMPROVE |
| 从网上 / GitHub 拿了个 skill，不确定能不能装 | ✅ VET |
| 从零写全新 skill，没有任何可提取的痕迹 | ❌ 用内置 `skill-creator` |
| 只是改个措辞 / 调个参数 | ❌ 直接编辑文件，别走流程 |
| 只想了解 skill 是什么 | ❌ 解释即可 |

## 已知边界（别高估它）

诚实写在文档里，比让人自己撞出来好：

- **引号内的载荷只降到 HIGH，不阻断。** 机器无法区分"引用一个形态"和"伪装成引用的命令"——协议文档自己就要引用红牌形态才能教人识别。这一档交给人，不猜。
- **混淆代码、运行时行为静态检不出。** RF07 只能人工读。
- **`--mode vet` 不是"安全认证"。** 它给的是分级提示与一个可追溯的结论，不是"通过即安全"的背书。
- **`evals` 只被数数量，不被判质量。** 硬门只验「≥2 个场景」，判断不了场景是否真实、是否含反向用例——而对路由型 skill 来说反向用例恰恰是最关键的（见 `references/skill-create.md`「形态变体：路由型 skill」）。这一项只能由写的人自己把关。
- **本包不附带 CI 配置。** 脚本提供 `--json` 与稳定退出码便于接入，但需自行接线。

## 与其他工具的关系

| 对象 | 关系 |
|------|------|
| `skill-creator`（WorkBuddy 内置） | 从零创建；本 skill 的 create 工艺已对齐它 |
| 本包 `validate_skill.py` | 替代 WorkBuddy 缺失的 `dz benchmark` |
| 人为质量门 | 脚本过了仍建议逐项过一遍——自动化只覆盖代码层 |

## 常见问题（FAQ）

**Q1：skill-create 和内置的 skill-creator 有什么区别？**

| 工具 | 适用场景 |
|------|---------|
| skill-create（本包） | **有素材**：执行痕迹、可合并的旧 skill、项目里现成的文档与脚本 |
| skill-creator（内置） | **从零创建**：既无痕迹也无素材 |

**Q2：改进一个 skill 需要多少轮？**

- 简单问题（FIX 模式）：1 轮，5–15 分钟
- 中等问题：2–3 轮，30–60 分钟
- 复杂问题：3–5 轮，可能该考虑拆分 skill

**Q3：审查通过就等于 100% 安全吗？**

不是。审查通过只表示"**未发现已知风险**"：检不出零日漏洞、检不出运行时行为、检不出掩盖良好的混淆代码。
装完仍需关注异常信号。见下方「已知边界」。

**Q4：怎么判断一个 skill 需要改进？**

信号：输出格式不符预期、总是漏掉某几步、触发条件不准（该触发不触发 / 不该触发却触发）、与其他 skill 功能重叠、用户说"效果不好"。

**Q5：可以同时改进多个 skill 吗？**

不建议。多变量同时变无法归因，你没法判断是哪一处改动起了作用。一次改一个。

**Q6：为什么没有自动评分 / benchmark？**

WorkBuddy 环境没有 `dz` 一类自动评分工具，所以质量门是**人工清单**（见各子协议兜底章节），不阻断流程、不强制任何外部评分。
若将来生态提供标准化评测能力，可作为 `validate_skill.py` 的补充，但当前以人工质量门为准。

## 许可证

MIT License — 详见 [LICENSE](LICENSE)

## 作者

zhl（融合自 skill-crystallizer / skill-evolve / skill-vetter 等开源 skill 演进方法论）

---

<p align="center">
  <sub>协议层负责判断，机器层负责定位 —— 机器是加速器，不是裁判。</sub>
</p>
