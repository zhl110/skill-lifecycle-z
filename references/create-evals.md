# Skill Create — 评测用例（人工质量门）

> **路径约定：** `<lifecycle>` 指本 skill 包根（定义见主入口 SKILL.md「路径约定」），脚本命令请直接替换为该路径。

> 本文件是 `skill-create` 子协议的人工评测规格，覆盖其两种模式 **CAPTURED（从执行痕迹提取）** 与 **DERIVED（合并现有 skill）**。
>
> **路由型**（项目里已有素材、只做入口）属于 CAPTURED 的形态变体，另有一条硬要求：`evals/basic.md` 必须含
> **至少 1 个反向场景**（说一句沾边但无关的话，确认没被误触发）。理由见 `skill-create.md` 的「形态变体：路由型 skill」——
> 这一形态的主要失败模式是**误触发**，不是做不出东西。
>
> 改进（skill-improve）与审查（skill-vet）的触发 / 路由评测见包根 `test-prompts.json`（由 `<lifecycle>/scripts/self_check.py` 自动校验路由）。
>
> 自动化校验一律走包内 `validate_skill.py`（硬门），不再依赖任何外部 `dz` 类 benchmark CLI：跑通即视为通过，无需 Grade A。

---

## Eval 1：CAPTURED 模式 — 从执行痕迹提取 Skill

**输入：** 用户刚跑完一个可复现任务（例如搭好一个 Starlight 文档站，含组件结构、MDX 引入、侧边栏配置），说：
「帮我把刚才的任务总结成 skill」

**预期行为：**
- 触发 CAPTURED 模式
- 分析执行痕迹：用了哪些工具、什么顺序、做了哪些关键决策
- 识别可复用模式（如「Starlight 文档脚手架」）
- 提取：name、description（含触发词）、协议步骤、when-to-use
- 脚手架建目录（手写或借助可用工具）
- 填充 SKILL.md（frontmatter 含 `name` + `description` + `metadata.version`）
- 跑 `validate_skill.py`（create 模式）并报告结果，全绿即过

**通过标准：**
- skill 名称是描述性的（如 `starlight-scaffold`，而非 `task-1`）
- 协议步骤与实际执行一致（非凭空编造）
- 反模式小节至少含 1 条来自真实痕迹的坑
- `validate_skill.py` 全绿（含 `evals/basic.md` ≥ 2 场景）

---

## Eval 2：DERIVED 模式 — 合并两个 Skill

**输入：** 「把 explore 和 structured-reasoning 合并成一个 research-with-reasoning skill」

**预期行为：**
- 触发 DERIVED 模式
- 分析两个源 skill 的交接点
- 创建复合协议：explore 负责采集、structured-reasoning 负责分析
- 定义数据流：explore 的输出喂给 reasoning 的输入
- 脚手架新建 SKILL.md，在 `metadata.source_skills` 中引用两个源

**通过标准：**
- `metadata.source_skills` 同时含 `explore` 与 `structured-reasoning`
- 复合协议不是简单拼接，有实际集成逻辑
- 新 skill 有自己独立的 when-to-use，与任一源 skill 区分开

---

## 评测执行说明

- 上述两条用例对应 `test-prompts.json` 的 `#1`（CAPTURED）与 `#2`（DERIVED），路由由 `self_check.py` 自动校验。
- 跑真实评测时，按 `skill-create.md` 的协议走完，再用 `validate_skill.py` 硬校验；脚本过了即视为通过，无需外部评分工具。
- 若痕迹模糊（用户只说「总结成 skill」但没给细节），先走 Step 0 挖掘内核，再进入对应模式。
