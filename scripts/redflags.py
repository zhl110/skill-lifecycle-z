#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redflags.py — skill-lifecycle-z 的**红牌单一真源**（Single Source of Truth）。

为什么存在（治理整改）：
  此前红牌定义散落三处——`skill-vet.md`（协议正文）、`vet-checklist.md`（速查勾选版）、
  `validate_skill.py` 的 SUSPICIOUS_PATTERNS（机器扫描）。三份手工维护，
  必然漂移（实测已发生：`su` 只在脚本里、静态发现的编码混淆漏检、
  文档声明「脚本会检出」但脚本实际上覆盖不全）。

  现在：红牌**只在本文件定义一次**，由它同时驱动
    ① 机器扫描（validate_skill.py 导入 PATTERNS）
    ② 文档生成/校验（self_check.py 用它核对两份文档是否同步）

分级（severity）——这是 C1 的核心修复：
  CRITICAL  命中即足以判定 DO NOT INSTALL（外传凭证 / 读取密钥 / 动态执行外部输入）
  HIGH      命中需人工重点核查，通常应 CAUTION
  MEDIUM    提示性，常见于正当用途
  MANUAL    **脚本检不出**，只能人工读正文（指令注入、混淆、运行时行为）

判定门（gate）：
  BLOCKING  命中即判定"拒装"——只有 CRITICAL 级
  REVIEW    命中必须人工核查才放行——HIGH 级
  INFO      仅提示——MEDIUM 级
"""

import re

# ---- 红牌定义：id / 标题 / 严重度 / 检测正则（None = 只能人工判）/ 人工判定要点 ----
# severity: CRITICAL | HIGH | MEDIUM
# gate    : BLOCKING | REVIEW | INFO
# pattern : 可静态检出的正则；None 表示「必须人工读正文」（MANUAL）
RED_FLAGS = [
    # ---------- CRITICAL：命中即拒装 ----------
    dict(id="RF01", title="外传凭证文件", severity="CRITICAL", gate="BLOCKING",
         # 判定：**凭证路径 + 外传动作**必须构成同一条命令链。
         # · 只提到凭证文件名（讲解 SSH 密钥结构的文档）→ 不命中本条
         # · 只读凭证不外传 → 命中 RF20（HIGH，需人工核查，不阻断）
         # · 读凭证并外传（cat ~/.ssh/id_rsa | curl -d @- …）→ 本条 CRITICAL
         pattern=r"(?:cat|cp|scp|rsync|type|Get-Content|read|tail|head|more)\s+[^\n]{0,40}"
                  r"(?:\.ssh[/\\]id_[a-z0-9_]+|id_rsa|id_ed25519|\.pem\b|\.netrc"
                  r"|\.aws[/\\]credentials|\.kube[/\\]config)"
                  r"[^\n]{0,40}(?:\||>|&&|;|curl|wget|nc\b|scp|POST|post|send|upload|exfil|Invoke-WebRequest)"
                  r"|"
                  r"(?:curl|wget|nc\b|scp|Invoke-WebRequest)[^\n]{0,60}"
                  r"(?:\.ssh[/\\]id_[a-z0-9_]+|id_rsa|id_ed25519|\.pem\b|\.netrc"
                  r"|\.aws[/\\]credentials|\.kube[/\\]config)",
         manual="向外部地址 POST 密钥/私钥内容"),
    dict(id="RF20", title="读取凭证文件（未外传）", severity="HIGH", gate="REVIEW",
         # 与 RF01 配套：**读取**凭证文件本身即需人工核查（协议红牌「无理由读取
         # ~/.ssh ~/.aws ~/.config」），但未构成外传链路时不阻断安装。
         # 只匹配**动作**（cat/cp/Get-Content 等），散文里提到路径不算。
         pattern=r"(?:cat|cp|scp|rsync|type|Get-Content|read|tail|head|more|vi|vim|nano)\s+"
                  r"[^\n]{0,40}(?:\.ssh[/\\][^\s]{0,30}|\.aws[/\\][^\s]{0,30}"
                  r"|\.kube[/\\]config|id_rsa|id_ed25519|\.pem\b|\.netrc"
                  r"|\.aws[/\\]credentials|\.env\b"
                  # Windows 侧
                  r"|%USERPROFILE%\\\.ssh|%APPDATA%\\[^ \t\"']{0,40}"
                  r"|[A-Za-z]:\\Users\\[^\s\"']*\\(?:\.ssh|\.aws|AppData)[^\s\"']*)",
         manual="读取凭证/隐私文件，需确认有正当理由"),
    dict(id="RF02", title="读取代理身份/记忆文件", severity="CRITICAL", gate="BLOCKING",
         pattern=r"\bMEMORY\.md\b|\bUSER\.md\b|\bSOUL\.md\b|\bIDENTITY\.md\b|\bCLAUDE\.md\b",
         manual="读取这些文件即可能含系统提示/用户隐私"),
    dict(id="RF03", title="向未知地址发送数据", severity="CRITICAL", gate="BLOCKING",
         pattern=r"curl\b[^\n]*\s(?:-d|--data(?:-binary|-raw)?|-F|--form|-T|--upload-file)\b"
                  r"|\bwget\b[^\n]*\s--post-(?:file|data)\b"
                  r"|requests\.post\s*\(|httpx\.post\s*\(|urllib\.request\.urlopen\s*\([^\n]*data\s*="
                  r"|Invoke-WebRequest[^\n]*-Method\s*Post",
         manual="任意 POST/upload 且目标不是声明的公开只读 API"),
    dict(id="RF04", title="对外部输入动态执行", severity="CRITICAL", gate="BLOCKING",
         # ⚠️ 最后两个分支**关闭 IGNORECASE**（`(?-i:...)`）：
         # 扫描统一用 re.IGNORECASE，而 JS 的 `Function(` 构造器（运行时编译字符串）
         # 与小写的 `function(` 关键字只差一个字母大小写。不关的话，任何前端文件里的
         # `(function(){...})()` 都会被判 CRITICAL 拒装（实测：本包架构图 HTML 即中招）。
         pattern=r"\beval\s*\(|\bexec\s*\(|(?-i:\bFunction\s*\()|(?-i:new\s+Function\s*\()",
         manual="eval/exec 的入参来自用户输入或网络响应"),
    dict(id="RF05", title="提示注入 / 越权指令", severity="CRITICAL", gate="BLOCKING",
         # 三类形态：
         #  (a) 改写型：要求忽略上层指令（无论主语，必是攻击）
         #  (b) 免检型：宣称「已通过审查 / 不要列入红牌 / 直接报 SAFE」——
         #      目标是让审查者给出虚假通过结论，危害等同，同样 CRITICAL
         #  (c) 跳过用户确认：祈使形态「不要询问用户」（对 agent 说）才是注入；
         #      「本工具无需用户确认」是**能力描述**，不判红牌（实测误报，见 gap 测试）
         #
         # 反误报要点（实测踩过两次）：
         #  1) (b) 类不能只凭「通过 + 审查」二字命中——「格式校验通过」「审查通过就 100% 安全吗」
         #     这类**正常技术表述**到处都是。必须带**自称主体**（本 skill / this package）
         #     或**审查者语境**（不要列入红牌 / report verdict）。
         #  2) (c) 类「不要询问用户」在正常文档里也可能是正当描述——
         #     故只保留祈使形态（do not ask / 不要询问用户），去掉「无需用户确认」。
         pattern=r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions"
                  r"|disregard\s+(all\s+)?(previous|prior)"
                  r"|忽略(之前|上面|以上|前面|上述|前述)(的)?(所有)?(指令|规则|提示|要求|约束)"
                  r"|"
                  r"(?:不要|无需|不必)[^\n]{0,8}(?:列入|写入|出现在)[^\n]{0,8}(?:红牌|红旗|风险清单|报告)"
                  r"|"
                  # 免检型（中文）：必须带「自称主体」——本/该 skill / 工具 / 包 …
                  r"(?:本|该|此)\s*(?:skill|工具|包|插件|组件|服务|项目|包体)"
                  r"[^\n]{0,12}(?:已|已经)?(?:通过|经过|完成)[^\n]{0,8}(?:审查|审计|检测|校验|核查)"
                  r"|"
                  # 免检型（英文）：自称主体 或 审查者语境
                  r"(?:this|the)\s+(?:skill|tool|package|plugin|component|project)"
                  r"[^\n]{0,24}(?:has|have)\s+(?:already\s+)?passed\s+(?:a\s+)?(?:security\s+)?"
                  r"(?:review|audit|inspection)"
                  r"|do\s+not\s+(?:list|report|include|flag)\s+[^\n]{0,30}(?:red\s+flags?|risk\s+list)"
                  r"|report\s+(?:the\s+)?verdict\s*:\s*safe"
                  r"|"
                  r"do\s+not\s+ask\s+(?:the\s+)?user"
                  r"|不要(询问|告诉|通知)用户",
         manual="正文试图改写审查者行为、跳过用户确认、抑制告警，或宣称自身已通过审查以换取放行"),

    # ---------- HIGH：命中需人工重点核查 ----------
    dict(id="RF06", title="提权执行", severity="HIGH", gate="REVIEW",
         pattern=r"\bsudo\b|\bdoas\b|\bpkexec\b|\brunas\b|Start-Process\s+.*-Verb\s+RunAs",
         manual="提权到 root / 管理员"),
    dict(id="RF07", title="任意代码执行 / 反混淆", severity="HIGH", gate="REVIEW",
         pattern=None,
         manual="混淆代码（压缩/编码/minified）、动态拼装命令行、运行时下载后执行"),
    dict(id="RF08", title="删除或改写系统文件", severity="HIGH", gate="REVIEW",
         pattern=r"\brm\s+-[rf]{1,2}\b|\bshred\b|Remove-Item\b[^\n]*-Recurse|del\s+/[sf]|Move-Item\b[^\n]*C:\\\\Windows",
         manual="删除/改写工作区外的系统目录"),
    dict(id="RF09", title="安装外部依赖", severity="HIGH", gate="REVIEW",
         pattern=r"\b(?:npm|pnpm|yarn|pip3?|brew|apt-get?|cargo|gem|go\s+get)\s+(?:install|add|i|get)\b"
                  r"|pip\s+install\s+[^\n]*http",
         manual="安装未在文档中列明的包（尤其从 URL 直接装）"),
    dict(id="RF10", title="硬编码凭证 / 密钥", severity="HIGH", gate="REVIEW",
         pattern=r"(?:api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}",
         manual="任何硬编码的 token / key / 密码字面量"),
    dict(id="RF11", title="凭证 / 会话数据访问", severity="HIGH", gate="REVIEW",
         pattern=r"\bcookies?\b|session_?id\b|keychain|钥匙串|Cookies\.sqlite|Login\s+Data",
         manual="读取浏览器 cookie / 会话存储"),
    dict(id="RF12", title="全局可写权限", severity="HIGH", gate="REVIEW",
         pattern=r"\bchmod\s+(?:-R\s+)?777|\bchmod\s+(?:-R\s+)?\+w\b|icacls\b[^\n]*/grant",
         manual="把路径设为世界可写"),
    dict(id="RF13", title="Windows 平台危险操作", severity="HIGH", gate="REVIEW",
         pattern=r"Invoke-Expression|\biex\s+|powershell\s+-enc\s+|cmd\s*/c\s+del\b|reg\s+delete\b|Set-MpPreference\s+-Disable",
         manual="Windows 专属：编码执行的 PowerShell、删注册表、关防护"),
    dict(id="RF14", title="裸 IP 地址请求", severity="HIGH", gate="REVIEW",
         pattern=r"(?<![\w.-])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])",
         manual="绕过 DNS 不做证书校验的直连（除非明确为本地服务）"),

    # ---------- MEDIUM：提示性，常见于正当用途 ----------
    dict(id="RF15", title="网络请求", severity="MEDIUM", gate="INFO",
         pattern=r"\bcurl\b|\bwget\b|\brequests\.|\burllib\b|\bhttpx\b|\bfetch\s*\(",
         manual="确认目标是声明过的公开只读 API"),
    dict(id="RF16", title="子进程调用", severity="MEDIUM", gate="INFO",
         pattern=r"os\.system|subprocess\.|popen\(|child_process|\bexecFile\b|shell\s*=\s*True",
         manual="确认命令参数不来自未清洗的外部输入"),
    dict(id="RF17", title="base64 编解码", severity="MEDIUM", gate="INFO",
         pattern=r"\bbase64\b|\batob\s*\(|\bbtoa\s*\(|Buffer\.from\([^)]*base64",
         manual="确认不是用来隐藏 payload"),
    dict(id="RF18", title="敏感目录访问", severity="MEDIUM", gate="INFO",
         # **跨平台**：Unix（~/.ssh、/etc/passwd）与 Windows（%USERPROFILE%\.ssh、
         # AppData、ProgramData）都要覆盖——本机主力平台是 Windows，
         # 只写 Unix 路径会让 Windows 侧的真实敏感目录访问完全漏检。
         pattern=r"~/\.ssh|~/\.aws|~/\.config|/etc/passwd|/etc/shadow"
                  r"|%APPDATA%|%LOCALAPPDATA%|%USERPROFILE%"
                  r"|[A-Za-z]:\\\\Users\\\\[^\s\"']*\\\\(AppData|\.ssh|\.aws|\.config)"
                  r"|\\\\Users\\\\[^\s\"']*\\\\(AppData|\.ssh|\.aws)",
         manual="确认有正当理由"),
    dict(id="RF19", title="读取环境变量中的密钥", severity="MEDIUM", gate="INFO",
         pattern=r"os\.environ(?:\.get)?\s*[(\[]\s*['\"]?(?:[A-Z_]*(?:KEY|SECRET|TOKEN|PASSWORD))",
         manual="确认只读自己声明需要的那个变量"),
    dict(id="RF21", title="包外符号链接", severity="CRITICAL", gate="BLOCKING",
         pattern=None,
         manual="链接指向包外（如 ~/.ssh、/etc/passwd、其他盘符）—— 安装后常驻，"
                "等于一条持久提权通道；等价于 skill-vet.md Step 4 的 ⛔ EXTREME。"
                "由 validate_skill.py 的链接检查检出（不靠文本模式）"),
]

# 只能人工判的红牌（pattern=None）
MANUAL_ONLY = [rf for rf in RED_FLAGS if rf["pattern"] is None]# 机器可检的红牌
MACHINE_CHECKABLE = [rf for rf in RED_FLAGS if rf["pattern"] is not None]


def patterns_by_severity(severity):
    """取某个严重度的 (pattern, label, severity) 列表，供 validate_skill.py 使用。"""
    return [(rf["pattern"], "%s [%s] %s" % (rf["title"], rf["id"], rf["severity"]), rf["severity"])
            for rf in MACHINE_CHECKABLE if rf["severity"] == severity]


def all_patterns():
    """全部机器可检模式。

    返回 (pattern, label, severity) **三元组** —— 严重度以结构化字段传递，
    **不从给人看的 label 文本反解**。理由：早前版本用正则从 label 里提取 severity，
    一旦标签格式调整（如 `标题 [RF01] CRITICAL` → 别处），全部模式会**静默降级为 MEDIUM**，
    安全门随之失效且不报任何错——这是最危险的失效模式。
    结构化传递 + `assert_severity_contract()` 断言可彻底防住这一整类回归。
    """
    return [(rf["pattern"], "%s [%s] %s" % (rf["title"], rf["id"], rf["severity"]), rf["severity"])
            for rf in MACHINE_CHECKABLE]


def assert_severity_contract():
    """断言：每条红牌的 severity 都能被扫描器**结构化**地取到，且与定义一致。

    这条断言是「安全门静默失效」这一类回归的最后一道防线。
    返回 (ok, problems)。
    """
    problems = []
    for pat, label, sev in all_patterns():
        if sev not in ("CRITICAL", "HIGH", "MEDIUM"):
            problems.append("红牌 %s 的 severity 非法: %r" % (label, sev))
        # label 里的严重度必须与结构化字段一致（防止两处不同步）
        m = re.search(r"\b(CRITICAL|HIGH|MEDIUM)\b\s*$", label)
        if not m:
            problems.append("红牌 label 未以严重度结尾，无法人工核对: %s" % label)
        elif m.group(1) != sev:
            problems.append("红牌 label 与结构化 severity 不一致: %s vs %s" % (m.group(1), sev))
    return len(problems) == 0, problems


def gate_for(severity):
    """严重度 → 判定门。"""
    return {"CRITICAL": "BLOCKING", "HIGH": "REVIEW", "MEDIUM": "INFO"}.get(severity, "INFO")


def blocking_ids():
    return [rf["id"] for rf in MACHINE_CHECKABLE if rf["severity"] == "CRITICAL"]


def review_ids():
    return [rf["id"] for rf in MACHINE_CHECKABLE if rf["severity"] == "HIGH"]


def all_ids():
    return [rf["id"] for rf in RED_FLAGS]


if __name__ == "__main__":
    print("红牌共 %d 条（机器可检 %d / 仅人工 %d）" % (
        len(RED_FLAGS), len(MACHINE_CHECKABLE), len(MANUAL_ONLY)))
    for sev in ("CRITICAL", "HIGH", "MEDIUM"):
        ids = [rf["id"] for rf in RED_FLAGS if rf["severity"] == sev]
        print("  %-8s %d 条: %s" % (sev, len(ids), ", ".join(ids)))
    print("仅人工判: %s" % ", ".join(rf["id"] for rf in MANUAL_ONLY))
