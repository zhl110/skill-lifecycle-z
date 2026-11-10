#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_common.py — skill-lifecycle-z 两个校验脚本的共享实现（零依赖，仅标准库）。

存在的理由（架构整改）：
  此前 `validate_skill.py` 与 `self_check.py` 各自实现了一套 frontmatter 解析器，
  且规则已产生分歧（一个要求 description 双引号包裹、另一个接受任意引号形态），
  导致「同一份 artifact 两条门禁判定不闭合」。本模块把解析与通用规则收敛为
  **唯一实现**，两个脚本共同引用，避免规则漂移。

对外接口：
  parse_frontmatter(text)  -> (data, err)      解析 frontmatter（含 metadata 嵌套 / 块标量）
  frontmatter_block(text)  -> str              取 frontmatter 原文块
  extract_description(fm)  -> str              取 description 完整值（兼容 | 与 > 块标量）
  count_scenarios(md)      -> int              统计 eval 中的**真实**场景数
  check_name(name)         -> (ok, msg)        name 规则校验
  strip_quotes(s)          -> str              去除首尾引号
"""

import re

# name 规则：小写字母 / 数字 / 中文（一~鿿）/ 连字符
NAME_RE = re.compile(r'^[a-z0-9一-鿿-]+$')

# 平台内置 skill-creator 的 quick_validate.py 用纯 ASCII hyphen-case；
# WorkBuddy 加载器实际接受中文 name。此处保留两套规则供按需提示。
PLATFORM_ASCII_NAME_RE = re.compile(r'^[a-z0-9-]+$')

# 触发词判定（description 里至少命中其一）
TRIGGER_RE = re.compile(r'use when|触发|not to use|not for|什么时候该用', re.IGNORECASE)

# eval 场景识别规则（真源，validate_skill.py 与文档文案共用同一口径）：
#   · 标题必须**含场景关键词**（场景 / scenario / 测试 / test），且
#   · 该标题下**必须有一段非空正文**（否则「## 场景1」空标题不算场景）
#   · **剥离围栏代码块**后再计数（代码块里的标题是示例，不是真实场景）
# 词边界用 \b，避免 "latest" / "contest" 里的 "test" 子串被误命中。
SCENARIO_KEYWORDS = ("场景", "scenario", "测试", "test")
SCENARIO_HEADER_RE = re.compile(
    r"^#{2,4}\s*.*?(?:\b场景\b|\bscenario\b|\b测试\b|\btest\b)", re.IGNORECASE | re.MULTILINE)
SCENARIO_ENTRY_RE = re.compile(r"输入\s*[:：].*?\n.*?预期\s*[:：]", re.IGNORECASE | re.DOTALL)
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def _strip_code_fences(md):
    """剥离围栏代码块（``` 或 ~~~），避免示例代码里的标题被计为场景。"""
    return FENCE_RE.sub("", md)


def count_scenarios(md):
    """统计 eval 中的**真实**场景数。

    旧实现把任意 2 个二级标题当作 2 个场景，导致「## 前置条件 / ## 后置条件」
    这类无场景内容的 evals 也能通过 create 硬门（已实测坐实）。
    后续又发现 5 条绕过路径：空标题、裸 `test` 子串（latest/contest）、
    围栏代码块内的标题等——现统一按「关键词 + 标题下有正文 + 剥离围栏」判定。
    """
    md = _strip_code_fences(md)
    # 标题计数：要求标题下至少有一行非空正文
    header_count = 0
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if not SCENARIO_HEADER_RE.match(line):
            continue
        # 该标题下必须有一段非空正文（到下一个同级或更高级标题为止）
        for nxt in lines[i + 1:]:
            if nxt.strip().startswith("#"):
                break
            if nxt.strip():
                header_count += 1
                break
    entry_count = len(SCENARIO_ENTRY_RE.findall(md))
    return max(header_count, entry_count)


def strip_quotes(s):
    """去除首尾成对的单/双引号。"""
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def frontmatter_block(text):
    """取 frontmatter 原文块。

    返回：块内文本 / `""`（有 frontmatter 但没有任何字段）/ `None`（没有 frontmatter）。

    ⚠️ 「空块」与「没有块」必须区分开。早期两种情况都返回 None，于是 `---` 紧跟 `---`
    的文件被报成「未以 --- 闭合」—— 它明明闭合了，诊断指向一个不存在的问题，
    用户会去翻分隔符而不是补 name / description。
    顺带兼容 CRLF（Windows 上手写过 SKILL.md 的人一定会遇到）。
    """
    m = re.match(r'^---[ \t]*\r?\n(.*?)\r?\n---', text, re.DOTALL)
    if m:
        return m.group(1)
    if re.match(r'^---[ \t]*\r?\n---', text):
        return ""
    return None


def extract_description(fm):
    """从 frontmatter 块中提取 description 的完整值（兼容块标量 | 与 >）。"""
    lines = fm.splitlines()
    out = []
    started = False
    for line in lines:
        if re.match(r'^description:\s*', line):
            started = True
            rest = line.split(':', 1)[1].strip()
            if rest and rest not in ('|', '>'):
                out.append(rest)
            continue
        if started:
            # 遇到下一个顶层 key（行首非空白 + 冒号）即结束
            if re.match(r'^\S', line) and ':' in line:
                break
            out.append(line)
    return '\n'.join(out)


def parse_frontmatter(text):
    """解析 frontmatter，返回 (data, err)。

    支持：
      - 扁平 key: name / description
      - metadata 嵌套块: metadata.version / metadata.status
      - description 块标量: description: | / description: >
    """
    fm = frontmatter_block(text)
    if fm is None:
        # 分成两种情形说清楚：根本没有块 vs 有开头没结尾。
        # 早期合并为「未以 --- 闭合」，对「压根没写 frontmatter」的文件是误导。
        if not text.startswith("---"):
            return None, ("缺少 frontmatter：文件必须以 --- 开头的 YAML 块，"
                          "且含 name 与 description")
        return None, "frontmatter 未闭合：开头有 ---，但找不到结尾的 ---"

    data = {}
    cur_key = None
    pending_block = None  # 正在收集块标量内容的 key

    for raw in fm.splitlines():
        line = raw.rstrip()
        if pending_block is not None:
            # 块标量续行：缩进行属于当前 key，空行也属于；顶格行则结束
            if line.strip() == "" or line[:1] in (" ", "\t"):
                data[pending_block] = (data.get(pending_block, "") + "\n" + line).strip("\n")
                continue
            pending_block = None

        if not line.strip():
            continue

        if re.match(r"^\s+\S", line):
            # 缩进行 → metadata 的子键
            if cur_key == "metadata" and ":" in line:
                k, v = line.strip().split(":", 1)
                data.setdefault("metadata", {})[k.strip()] = strip_quotes(v)
            continue

        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "metadata":
                cur_key = "metadata"
                # 内联流式写法：metadata: {version: "1.0", status: "draft"}
                if v.startswith("{") and v.endswith("}"):
                    inner = v[1:-1]
                    md = {}
                    for part in re.split(r",(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)", inner):
                        if ":" in part:
                            kk, vv = part.split(":", 1)
                            md[kk.strip()] = strip_quotes(vv)
                    data["metadata"] = md
                else:
                    data["metadata"] = {}
            else:
                cur_key = k
                if v in ("|", ">"):
                    data[k] = ""
                    pending_block = k
                else:
                    data[k] = strip_quotes(v)

    return data, None


def read_text(path):
    """健壮读文本文件。

    **不能用 `open(..., encoding="utf-8")`**：包内若存在非 UTF-8 文件
    （UTF-16 载荷、旧编码文档），会直接抛 UnicodeDecodeError 让脚本**崩溃**，
    而不是报告问题——崩溃会掩盖真实结论（实测踩过）。
    正确做法：解码失败时退回 latin-1（永不抛错）。
    """
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, encoding="latin-1") as f:
            return f.read()
    except OSError:
        return ""


def check_name(name):
    """校验 skill name。返回 (ok, msg)。"""
    if not NAME_RE.match(name):
        return False, "name '%s' 非法：仅允许小写字母/数字/中文/连字符" % name
    if name.startswith('-') or name.endswith('-') or '--' in name:
        return False, "name '%s' 不能以连字符开头/结尾，也不能含连续连字符" % name
    return True, "name = %s" % name


# 纳入扫描的文本扩展名（**真源**：validate_skill.py 的红牌扫描 与
# self_check.py 的残留扫描 共用同一份，两门覆盖面必须一致——
# 否则「红牌扫得到但残留扫不到」这类不一致会变成盲区）。
SCAN_EXTS = (
    '.md', '.py', '.sh', '.bash', '.zsh', '.fish', '.js', '.mjs', '.cjs', '.ts',
    '.tsx', '.jsx', '.bat', '.cmd', '.ps1', '.rb', '.pl', '.php', '.lua',
    '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env',
    '.txt', '.html', '.htm', '.svg', '.xml', '.sql',
    '.b64', '.base64', '.enc', '.encoded', '.hex', '.dat', '.data', '.bin',
)
