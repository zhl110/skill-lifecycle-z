# Skill Publish — 安装与归档（参考协议，按需读取）

> **路径约定：** `<lifecycle>` 指本 skill 包根（定义见主入口 SKILL.md「路径约定」），脚本命令请直接替换为该路径。

**前置条件（全部满足才允许进入本协议）：**

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | 已完成 `skill-vet` 审查并得到明确 VERDICT | 审查报告存在，VERDICT 非 DO NOT INSTALL |
| 2 | 协议层红线**逐条人工核对通过** | 红线不依赖机器检出——脚本无命中 ≠ 红线不成立（见 skill-vet.md 的 Step 2 内「判定门（两层，协议层优先）」） |
| 3 | 格式校验通过 | `python <lifecycle>/scripts/validate_skill.py <目录> --mode vet` 退出码 0 |
| 4 | 用户明确同意安装 | 用户确认 |

> ⚠️ **⛔ EXTREME 一律不装。** 「用户坚持」不是豁免理由——若认为分类有误，先修正分类再重新评估。

---

## 安装位置选择

| 来源类型 | 目标位置 | 说明 |
|---------|---------|------|
| 本地自建 skill | `~/.workbuddy/skills/<name>/` | 用户级，全项目可用 |
| 项目级 skill | `<项目>/.workbuddy/skills/<name>/` | 仅本项目可用，优先于用户级 |
| 从 marketplace 安装 | `~/.workbuddy/skills/<name>/` | **安装后须标记 `userModified`**（见下） |

**同名冲突处理：** 目标已存在同名 skill → **必须先问用户**（覆盖 / 改名 / 取消），不得静默覆盖。

---

## 安装步骤

### 1. 备份（可回滚的前提）

若目标位置已存在同名 skill，先备份：

```bash
# 用 git 更稳妥；无 git 时复制目录
cp -r ~/.workbuddy/skills/<name> ~/.workbuddy/skills/<name>.bak.$(date +%Y%m%d-%H%M)
```

### 2. 复制 + 落盘验证

**先确认产物干净** —— 裸 `cp -r` 会把 `.git/` `node_modules/` 原样搬过去，
而这些目录既不参与扫描也不参与 seal，等于给载荷开了一条后门
（`--mode vet` 已把这类产物判 CRITICAL，但这里再确认一次）：

```bash
ls -a <待装 skill 目录> | grep -E '^\.git$|^\.venv$|^venv$|^node_modules$' \
  && echo "❌ 产物不干净，停止安装" && exit 1
```

**用排除法复制**（不要用裸 `cp -r`）：

```bash
# 方式一：tar 管道（Windows 10+ 自带 tar，跨平台可用）
( cd <待装 skill 目录> && tar cf - \
    --exclude=.git --exclude=node_modules --exclude=__pycache__ --exclude=.venv . ) \
  | ( cd ~/.workbuddy/skills/<name>/ && tar xf - )

# 方式二：rsync（有的话更直观）
rsync -a --exclude=.git --exclude=node_modules --exclude=__pycache__ \
  <待装 skill 目录>/ ~/.workbuddy/skills/<name>/

ls -la ~/.workbuddy/skills/<name>/          # 确认文件齐全且无 .git
```

> 为什么强调这个：seal 的语义是「审的东西 == 装的东西」。若安装包含了 seal 没覆盖的目录，
> 这个等式就断了 —— 审查得再仔细也拦不住藏在 `.git/` 里的东西。

### 3. 内容指纹核对（堵住「审查后被改」的时间窗）

审查与安装之间存在 **TOCTOU**（time-of-check to time-of-use）窗口：
审查通过后、复制前，待审目录可能被改动（供应链更新、并发写入、误操作）。
**因此复制前后都要核对内容指纹**，不一致就重新走审查。

```bash
# ① 审查完成时：记录内容指纹（写进审查报告）
python <lifecycle>/scripts/validate_skill.py <待装目录> --seal
# 输出：SEAL: <sha256>

# ② 安装前：核对指纹
python <lifecycle>/scripts/validate_skill.py <待装目录> --verify-seal <上一步的 sha256>
# 一致 → 退出码 0（审查结论仍有效）
# 不一致 → 退出码 3 → **作废审查结论**，重新审查
```

> 指纹只覆盖**文件内容**（路径 + 内容的 SHA-256），不覆盖 mtime 等元数据，
> 因此复制 / 同步不会改变指纹，而**内容改动一定会改变**。
> 不要用「差异不大，应该是元数据」来自行放行——脚本判定不一致就是不一致。

### 4. 安装后格式复验（**必做**）

```bash
python <lifecycle>/scripts/validate_skill.py ~/.workbuddy/skills/<name> --mode vet
```

> 安装路径与源路径可能不同（symlink / 复制），**装完必须再验一次**——
> 装的位置不对、文件没复制全、编码损坏，都只会在这一步暴露。

### 5. marketplace 来源：标记 `userModified`

若 skill 来自 marketplace（非本地创建），改完并**成功保存后**必须标记，否则平台自动更新会静默覆盖：

1. 在目标 skill 目录找 marketplace 元文件：`_skillhub_meta.json`（BuiltinMarket / SkillHub 源）或 `_knot_meta.json`（Knot 源）。
2. 读该 JSON，把 `"userModified": true` 写回（原无该字段则新增）。
3. 保存后告知用户：改动已保存，未来 marketplace 更新会先询问再覆盖。

> 只在文件真的写盘后再标记，不要提前或推测性标记。本地创建的 skill（无上述元文件）跳过此步。

---

## 归档与留档

安装完成后，把审查与安装记录落到**受控路径**（不要写进待审 skill 内部——那会污染被审物，且可能被后续更新覆盖）：

```
<工作目录>/
├── <skill-name>-vet-report.md     # 审查报告：红牌核对结果 + VERDICT + 命中项
└── <skill-name>-install-log.md     # 安装记录：来源 / 版本 / 时间 / 安装位置 / userModified 标记情况
```

> 审查报告里**只引用被审 skill 的相对路径**，不要嵌入绝对路径——
> 绝对路径会让报告本身携带环境信息，且在别的机器上失效。

---

## 🛑 CHECKPOINT：安装前确认

| # | 节点 | 触发条件 | 确认内容 |
|---|------|---------|---------|
| CP-P1 | 安装前 | 审查通过、准备复制 | 展示安装位置 / 是否覆盖同名 skill / 复验命令，等用户确认 |
| CP-P2 | 安装后 | 文件已落盘 | 展示复验结果与安装位置，确认加载正常 |

**违反 CHECKPOINT 的信号：** 如果你在没有用户确认的情况下直接安装了 skill，立即停下，回溯到 CP-P1。

---

## 异常处理

| 场景 | 一线修复 | 兜底 |
|------|---------|------|
| 目标已存在同名 skill | 问用户：覆盖 / 改名 / 取消 | 改名（加版本后缀） |
| 复制后复验失败 | 检查文件是否复制完整 / 编码是否损坏 | 从备份恢复，排查后再试 |
| marketplace 自动更新覆盖了改动 | 重新标记 `userModified` | 告知用户该来源的更新策略 |
| 安装后 skill 未被加载 | 检查目录名是否与 frontmatter `name` 一致 | 修目录名或 name（两者保持一致） |
| 用户要求安装 ⛔ EXTREME 的 skill | **拒绝** | 说明红线不可协商；请其提供正当场景或换用替代方案 |
| 磁盘写入失败 | 检查权限与磁盘空间 | 换路径重试，或告知用户手动安装 |

---

## 发布后跟踪

| 时间 | 检查项 | 目的 |
|------|--------|------|
| 安装后立即 | 运行一次，确认输出正常 | 基础功能验证 |
| 1 周后 | 检查是否有异常行为（网络 / 文件 / 性能） | 检测延迟恶意代码 |
| 首次更新 | 重新审查变更 | 新版本可能引入风险 |

**异常信号：** 网络请求异常 / 文件访问异常 / 性能异常 / 行为与描述不符。

---

## 🚫 反模式 / 不要做的事

| 不要 | 原因 | 正确做法 |
|------|------|---------|
| 跳过审查直接装 | 安全风险 | 先 vet，再 publish |
| 因脚本「无命中」就认为安全 | 机器检不出混淆、运行时行为、指令层 | 协议层红线逐条人工核对 |
| 静默覆盖同名 skill | 丢失用户已有工作 | 先问用户 |
| 装完不复验 | 装错位置/文件不全只在复验暴露 | 装完必跑一次校验 |
| 用「用户坚持」豁免 EXTREME | 红线被一次性掏空 | 红线不可协商 |
| 把报告写进待审 skill 内部 | 污染被审物 / 可能被更新覆盖 | 写到受控工作目录 |

---

MIT License，详见包根 `LICENSE`。
