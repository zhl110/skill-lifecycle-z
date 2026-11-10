---
name: skill-lifecycle-z
description: "统一管理 skill 的全生命周期：从执行痕迹提取（CAPTURED）/ 合并现有 skill（DERIVED）来创建、演进式改进（skill-improve）、安装前安全审查（skill-vet）。Use when 用户提到'从痕迹提取'、'结晶skill'、'总结成skill'、'从执行痕迹创建skill'、'合并skill'、'组合skill'、'改进skill'、'修复skill'、'skill效果不好'、'优化skill'、'审查skill'、'审计skill'、'vet skill'、'skill生命周期'、'skill管理'、'安全审查'。注：从零设计全新 skill（无执行痕迹、无可合并对象）→ 交给内置 skill-creator，不归本 skill。"
metadata:
  version: "2.3.0"
  format: "workbuddy-native"
---

# Skill Lifecycle — 全生命周期管理

Skill 从创建到废弃的全流程管理。一个工具箱覆盖三大场景。

## 路径约定

> 下文及 `references/` 中的 `<lifecycle>` 均指本 skill 包根目录。本机已通过 symlink 注册到 `~/.workbuddy/skills/skill-lifecycle-z`，可直接用该路径替换 `<lifecycle>`（例如 `<lifecycle>/scripts/validate_skill.py` 即 `~/.workbuddy/skills/skill-lifecycle-z/scripts/validate_skill.py`）。

## When to use this skill

**这是唯一权威路由表**——先按用户的话对上表，再看下面的判别问句区分模式。

| 场景 | 触发词（用户可能的说法） | 走哪条 | 关键判别 |
|------|--------|--------|---------|
| 从执行痕迹提取 skill | "从痕迹提取"、"结晶skill"、"总结成skill"、"把刚才的任务总结成skill"、"从执行痕迹创建skill" | skill-create (CAPTURED) | 有可复用的执行痕迹 |
| 合并多个 skill | "合并 skill"、"组合 skill"、"把 X 和 Y 合并" | skill-create (DERIVED) | 有 2+ 个可合并对象 |
| 迭代改进 skill | "改进 skill"、"优化 skill"、"skill 效果不好" | skill-improve（标准路径） | 不知道具体问题在哪 |
| 快速修复问题 | "skill 有问题"、"输出格式不对"、"总是漏步骤"、"这个引用过期了" | skill-improve (FIX 模式) | 知道具体问题 |
| 安装前安全审查 | "审查 skill"、"审计 skill"、"安全检查"、"vet skill"、"这个 skill 能装吗" | skill-vet | 装之前问安全性 |
| 完整走一遍 | "帮我做一个完整的skill"、"从零到能用" | create → improve → vet → publish | 未指定阶段 |
| 审查通过后安装 | "装这个 skill"、"安装它"、"装到 skills 目录" | skill-publish | 已过审查，准备落地 |

**Do NOT use when:**
- 创建全新的 skill（无执行痕迹）→ 用内置 **skill-creator**
- 简单修改一个配置 / 改一段文字 → 直接编辑
- 用户只是想了解 skill 是什么 → 解释即可

---

## 决策树：从哪里开始？

```
用户想做什么？
│
├─ "帮我创建一个skill"
│   ├─ 有执行痕迹？ → skill-create (CAPTURED)
│   ├─ 有多个skill想合并？ → skill-create (DERIVED)
│   ├─ 项目里已有素材，只要个入口？ → skill-create (CAPTURED + 路由型)
│   └─ 都没有（从零设计，无痕迹、无素材、无合并对象） → skill-creator（不归本 skill）
│
├─ "这个skill效果不好"
│   ├─ 知道具体问题？ → skill-improve (FIX模式)
│   └─ 不知道哪里有问题？ → skill-improve (标准路径)
│
├─ "这个skill安不安全？"
│   └─ → skill-vet
│
├─ "帮我做一个完整的skill"
│   └─ → 全流程：create → improve → vet
│
└─ 不确定
    └─ 问用户：你想创建、改进、还是审查？
```

> 上面的决策树只负责**判别模式**（哪个分支）；触发词对照见上方「When to use this skill」表，**不要分别维护两份**。

> ⚡ **IMPROVE 的效率关键**：能说出「哪个输入 → 哪个错误输出」，就直接走 **FIX**，别从五步循环开始。
> 观察是为了发现**未知**问题，不是为了确认**已知**问题。有具体案例却跑完整循环 = 40 分钟干 3 分钟的活。
> **最锋利的收尾手段**：标准路径里务必跑「使用者视角穷举自审」——站到真实使用者座位上把毛病全挑出来、改到挑不出为止（详见 `references/skill-improve.md`）。本 skill 实测极有效，强烈建议作为常驻步骤。

---

## 完整生命周期流程

当用户说"帮我做一个 skill"且没有明确阶段时：

```
CREATE ──CP5──▶ IMPROVE ──CP5──▶ VET ──CP4──▶ PUBLISH
```

**每步输入 / 输出（明确交接物，避免阶段间职责模糊）：**

| 阶段 | 输入 | 输出 |
|------|------|------|
| CREATE | 用户的执行痕迹 / 待合并 skill 列表；CP1 确认从痕迹提取 / 合并 / 从零 | 新 skill 的 `SKILL.md`（含 frontmatter）+ `evals/basic.md`（create 模式硬门，≥2 场景） |
| IMPROVE | 目标 skill 路径 + 具体问题或测试结论；CP2 备份确认并展示本轮改动 | 改进后的 `SKILL.md` + before/after 对比（CP3 等用户确认再继续） |
| VET | 待审 skill 目录 + 来源信息（URL / 作者 / stars / 更新时间） | 风险报告（红 / 黄 / 绿分级）+ VERDICT（SAFE / CAUTION / DO NOT）+ 人工确认项（CP4） |
| PUBLISH | 审查通过（CP4，协议层红线已人工逐条核对）且用户明确同意安装的 skill | 安装到目标 skill 目录（如 `~/.workbuddy/skills/`）+ **装完复验** + 审查/安装记录留档（详见 `references/publish.md`） |

**每步完成后确认：**
- CP5：是否进入下一步？（create→improve→vet）
- 用户说"可以了" → 停在当前阶段

---

## 与其他 skill / 工具的配合

| 配合对象 | 场景 | 说明 |
|-----------|------|------|
| skill-creator（WorkBuddy 内置） | 从零创建 skill（无任何执行痕迹） | 先由 skill-creator 产出初版，再回到本 skill 做改进 / 审查 |
| 人工质量门（本 skill 内置） | 验证创建 / 改进质量 | WorkBuddy 环境无自动化 benchmark，一律走 references/ 中的人工质量门清单 |
| 你自己的笔记 / 会议纪要 / 执行痕迹 | 提炼可复用模式 | 作为"从痕迹创建"的输入源，沉淀为 skill |

---

## 版本管理

每次改动目标 skill 都要 bump `metadata.version`（补丁 `+0.0.1` / 结构性 `+0.1.0`，见 `references/skill-improve.md`）。
版本号档位含义（0.1.0 初版 / 0.2.0 加功能 / 1.0.0 稳定 / 2.0.0 重构）见 `README.md`「版本号怎么升」。

---

## 质量门说明（重要）

自动化 benchmark 工具（如 Claude Code 生态的 `dz`）在 WorkBuddy 环境中**不可用**，
因此创建 / 改进一律走**人工质量门**（见各子协议的兜底章节），不阻断流程、不强制任何外部评分。

---

## 🛑 CHECKPOINT：关键决策前确认

**主入口（全局生命周期门，CP1–CP5）** —— 跨阶段的切换确认：

| # | 节点 | 触发条件 | 确认内容 |
|---|------|---------|---------|
| CP1 | 创建 skill 前 | 用户说"帮我做一个 skill" | 确认是从痕迹提取、合并现有、还是从零写 |
| CP2 | 改进 skill 前 | 即将修改目标 skill | 备份确认 + 展示本轮要改什么 |
| CP3 | 每轮改进后 | 完成一轮改写 | 展示 before/after 对比，等用户说好再继续 |
| CP4 | 审查结论后 | 完成安全审查 | 展示风险等级和红牌，等用户决定装不装 |
| CP5 | 全流程切换 | 一个阶段完成要进入下一阶段 | 确认用户是否继续 |

**子协议内的局部门（各自独立编号空间）** —— 进入某个子协议后按该协议的表执行：

| 命名空间 | 定义位置 | 覆盖的门 |
|---------|---------|---------|
| `CP-C1..C3` | `references/skill-create.md` | 创建协议内的模式确认 / 元数据确认 / 产出确认 |
| `CP-I1..I4` | `references/skill-improve.md` | 改进协议内的路径选择 / 方案确认 / 每轮对比 / 收敛确认 |
| `CP-V1..V3` | `references/skill-vet.md` | 审查协议内的路径确认 / 红牌确认 / 安装确认 |
| `CP-P1..P2` | `references/publish.md` | 安装协议内的安装前确认 / 安装后复验确认 |

> 引用门时写全编号（如「回溯到 CP-I2」），不要只写「CP2」——主入口与子协议的编号不同。

**违反 CHECKPOINT 的信号：** 如果你在没有用户确认的情况下连续做了 2 个以上阶段的操作，立即停下，回溯到上一个 CHECKPOINT。

---

## 异常处理

| 场景 | 一线修复 | 兜底 |
|------|---------|------|
| 目标 skill 不存在 | 确认名称拼写，检查 skills 目录 | 询问用户提供正确名称 |
| 改进 3 轮仍无改善 | 检查是否修"真实问题"而非"直觉优化" | 尝试探索性重写 |
| 测试 prompt 跑不通 | 简化 prompt 到最小可用版本 | 手动模拟执行流程 |
| 3 轮还不收敛 | 职责太宽/测试矛盾/能力限制 | 拆分 skill 或诚实告知 |
| dz CLI 不可用 | 走手动脚手架 + 人工质量门 | 告知用户后续可安装 dz |
| skill 目录结构不完整 | 按模板补建缺失文件 | 创建最小可用版本 |
| 权限审查不确定 | 提升一级风险等级处理 | 标记为需人工确认 |
| 多个 skill 高度相似 | 分析差异点，判断是否合并 | 保留功能更全的那个 |
| 用户跳过 CHECKPOINT | 提醒用户确认风险 | 记录日志，继续执行 |

---

## 工具脚本速查

| 场景 | 命令 | 判定标准 |
|------|------|---------|
| **create** 之后 | `python <lifecycle>/scripts/validate_skill.py <目标目录>` | 完整硬门：格式 + 触发词 + metadata.version + 反模式小节 + `evals/basic.md` ≥2 个**真实场景**。全绿才算创建完成 |
| **improve** 之后 | `python <lifecycle>/scripts/validate_skill.py <目标目录> --mode improve` | 只要求**原有内容没被改坏**；不强制补齐目标 skill 本来就没有的 evals / 反模式小节（改进既有 skill 别被误判为不合格） |
| **vet** 审查外部 skill | `python <lifecycle>/scripts/validate_skill.py <目标目录> --mode vet` | 创作规范类降级为警告；跳过 evals；额外做红牌扫描——**不只是提示**：CRITICAL 命中即**退出码 2（DO NOT INSTALL）**，HIGH 须人工核查 |
| **本 skill 自检** | `python <lifecycle>/scripts/self_check.py` | 9 项：frontmatter / 引用表双向 / 测试路由 / 生态残留 / 脚本齐全 / 文档-实现契约 / 红牌三处一致 / 同源清单一致 / 包内引用无悬空 |

通用选项：`--json` 输出结构化报告（可接 CI）、`--seal` / `--verify-seal` 内容指纹、`--help` 查看用法。
退出码 `0` 通过 / `1` 格式校验未通过 / `2` 拒装（CRITICAL 命中）或参数错误 / `3` seal 不一致。

> ⚠️ **vet 模式做的是「分级提示」，不是判决**。指令层风险（正文指示 agent 读凭证、外发数据、忽略上层指令）
> **能被扫到**，但「引用 vs 实施」只能由人分辨：载荷**裸露**在正文 → CRITICAL 拒装；
> 载荷**封在引号内** → 只降到 HIGH，必须人工确认它不是伪装成引用的命令。
> 见 `references/vet-checklist.md` 的「指令层红牌」。

---

## Reference Files（按需加载）

| 文件 | 内容 | 何时加载 |
|------|------|---------|
| `references/create-templates.md` | SKILL.md 模板、Description 写法、Review Checklist | 创建 skill 时 |
| `references/create-evals.md` | 评测用例（CAPTURED/DERIVED） | 验证创建质量时 |
| `references/improve-checklist.md` | 每轮改进前自检、收敛判断、何时停止 | 改进 skill 时 |
| `references/vet-checklist.md` | 审查检查清单（4 步 + 输出报告） | 审查 skill 时 |
| `references/skill-create.md` | 创建子协议完整协议（CAPTURED/DERIVED） | 进入创建时 |
| `references/skill-improve.md` | 改进子协议完整协议（标准/FIX） | 进入改进时 |
| `references/skill-vet.md` | 审查子协议完整协议（4 步 + 指令层红牌） | 进入审查时 |
| `references/publish.md` | 安装与归档协议（安装前确认 + 复验 + 留档） | 审查通过、准备安装时 |

**加载原则：** 不要全量加载 references/，根据当前任务按需读取对应文件，节省上下文。

> 📊 **想先看全貌，别读 references/**：包内有两张**给人看**的交互图，在 `assets/` 下（不是协议，agent 不需要读）：
> `assets/architecture.html` 讲**结构**（分成哪几层、谁依赖谁），`assets/workflow.html` 讲**走法**（什么情况走哪条路、哪里会被拦下）。
> 用浏览器打开，点节点看细则。比在 8 份协议之间跳转更快建立整体认识。

## 留档与素材（给人看，agent 不需要读）

这两类目录**不是协议**：内容全部来自本文件与 `references/`，是同一批信息的视觉 / 历史再表达。
读它们理解不了「现在该怎么做」——那是 `references/` 与 `scripts/` 的职责；两者冲突时以协议与实现为准。

**历史留档（`records/`）**：`records/skill-lifecycle-z-多专家审查研究报告.md`（v2.0.0 定稿时的 7 专家审查与修复过程快照）、
`records/skill-lifecycle-z-darwin-card.html`（某时点评测卡，不是当前质量的证明）。里面的用例数 / 行数 / 评分反映当时状态，**不随实现更新**。

**图示（`assets/`）**：`assets/architecture.html` 讲结构（分几层、谁依赖谁）、`assets/workflow.html` 讲走法（走哪条路、哪里被拦）、
`assets/skill-anatomy.svg` 讲形态（四档：纯文本 → +参考 → +脚本 → +工程化）。浏览器打开前两张可点节点看细则；
架构图里的红牌矩阵受 `self_check.py` 校验（编号集合与真源全等），不会过期。

**宣传素材（`assets/`）**：`assets/01.jpg` 四道门（封面）、`assets/02.jpg` 红牌墙、`assets/03.jpg` 单一真源、
`assets/04.jpg` 筛网拦截（竖版）、`assets/05.jpg` 判定印章。**图里没有任何文字是故意的**（生图写中文必糊，标题后期叠）。
配文禁区：04 说「拦截」不说「过滤」（画面只有挡住、没有筛出）；03 说「一个源、多处落点、落点完全一样」，
**别宣称「精确一一对应」**（光束数与环数并不严格相等）。完整用途表见 `README.md`。

> 上面点名的文件同样被自检覆盖（必须在此列出，否则算死件）—— **新增目录不等于免责区**。

---

## 第一次用？看这里

- **想先看全貌** → 浏览器打开 `assets/architecture.html`（结构）或 `assets/workflow.html`（走法）。
- **想知道标准 skill 该有哪些文件** → 看 `assets/skill-anatomy.svg` 的四档形态。
- **想直接开工** → 说一句人话即可（「帮我把刚才的任务总结成 skill」/「这个 skill 效果不好」/「这个 skill 安不安全」），
  按上方「When to use」表自动分流。
- **上手步骤、成功度量、常见问题、版本号档位** → 都在 `README.md`（给人看的说明书，不是协议）。

## 🚫 反模式 / 不要做的事

| 不要 | 原因 | 正确做法 |
|------|------|---------|
| 一次性重写整个 skill | 多变量同时变无法归因 | 每轮只改 1-2 个核心模式 |
| 未观察到问题凭直觉优化 | 可能越改越糟 | 必须基于真实测试 |
| 硬凑 N 轮 | 新问题数连续 2 轮为 0 且目标模式命中数归零 → 已触顶 | 见好就收 |
| 修表面 bug 不提炼模式 | 补丁覆盖不了新 prompt | 找共性根因 |
| 改 skill 前不备份 | 改坏了无法回滚 | git 分支或备份 |
| 跳过 CHECKPOINT | 用户失去控制权 | 每个关键节点都确认 |

---

MIT License，详见 `LICENSE`。
