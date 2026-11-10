#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_residues.py — 「Claude Code 生态残留」模式表的**独立模块**（零依赖）。

为什么独立成文件（代码审查 C1 根治）：
  此前模式表直接写在 self_check.py 里，导致扫描器必须「字面书写」自己要找的模式串，
  于是不得不引入**自指豁免**（把自己的模式定义块抹掉）。而豁免逻辑一旦写错
  （实测：marker 字符串在文件里出现两次 → 从第二处一直抹到文件末尾，
  扫描器自身后半段完全不被扫描，且仍输出「✅ 无残留」的虚假保证），
  就是**门禁工具在关键路径上给出虚假的安全保证**——比普通 bug 更危险。

  把模式表移到独立模块后：
    · self_check.py 只 import，不字面书写任何模式串 → **自指需求从根上消失**
    · 不再需要任何豁免逻辑 → 不存在「豁免失控」这一整类风险
    · 模式表可被单独审阅（单一真源）

模式只收录「结构性」Claude Code 生态残留（路径 / 插件 / 命令标记）。
刻意不收录 `dz`：它是 Claude Code 生态的 benchmark CLI，而非路径/插件标记；
本 skill 多处用「WorkBuddy 无 dz / dz 不可用」作教学说明，若把 dz 纳入自动扫描，
会因自身正确说明而误报失败。对「硬编码依赖外部 CLI（如 dz）」的审查改由
references/vet-checklist.md 的人工红牌项覆盖，不在自动扫描层处理。
"""

# Claude Code 生态的结构性残留特征
FORBIDDEN_RESIDUES = (
    r"~/\.claude",
    r"agentskills\.io",
    r"daemon-z",
    r"@anthropic-ai",
    r"\.claude/commands/",
    r"\.claude-plugin/commands/",
    r"\.claude-plugin",
    r"argument-hint",
)
