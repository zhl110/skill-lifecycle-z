#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-lifecycle-z 自检脚本（零依赖，仅用标准库）

用途：
  1. 校验 SKILL.md frontmatter 合法（name / description / metadata.version）。
  2. 校验 SKILL.md「Reference Files」表中列出的文件都存在。
  3. 校验 test-prompts.json 结构合法，且每条 prompt 的 command 能映射到
     references/<command>.md 子协议文档。
  4. 扫描活跃文件，确认无 Claude Code 生态残留（检测的路径 / 插件 / 命令标记见下方
     FORBIDDEN_RESIDUES；本文件自身的模式定义块自动豁免，避免自指误报）。

退出码：全部通过返回 0；任一项失败返回 1。

用法：
  python scripts/self_check.py
  python scripts/self_check.py --json      # 输出 JSON 报告
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import SCAN_EXTS, parse_frontmatter, read_text  # noqa: E402  共享解析器/扩展名真源/健壮读
from _residues import FORBIDDEN_RESIDUES  # noqa: E402  残留模式表在独立模块，避免自指豁免

# 解析真实路径（穿透 symlink，确保从 ~/.workbuddy/skills/ 也能正确定位包根）
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# 残留模式表见 scripts/_residues.py（独立模块）。
# 放在独立模块的用意：本文件不再**字面书写**任何待查模式串，
# 因此不需要「自指豁免」——而自指豁免一旦写错就会让扫描器在自己身上失效
# （曾实测：豁免区间从第二处 marker 一直覆盖到文件末尾，扫描器自身后半段
#   完全不被扫描，却仍输出「✅ 无残留」的虚假保证）。
# 详见 scripts/_residues.py 的模块文档。

# 活跃文件才扫描残留（CHANGELOG 历史条目保留旧账，不查）
# 改为**自动发现**而非硬编码清单：扫描包内所有活跃源文件，
# 只排除「历史/说明性」文件。硬编码清单会漏掉新增文件
# （实测曾漏掉 evals/basic.md、test-prompts.json、scripts/*.py）。
ACTIVE_FILES_EXCLUDE = {
    "CHANGELOG.md",      # 历史条目保留旧账（有意豁免）
    "LICENSE",
    # README.md **不排除** —— 它同样是活跃文档，可能含残留路径
    # （早期版本注释写「仍扫描」但实际被排除，属注释与实现不一致）。
    #
    # 残留模式表本身：它是「检测器定义」，天然字面书写了所有待查模式串。
    # 模式表已独立成模块，因此**只需排除这一个文件**，
    # 不再有「自指豁免区间可能覆盖过大」的风险。
    "scripts/_residues.py",
}


def collect_active_files():
    """自动发现需要扫描残留的活跃文件（相对包根的 posix 路径）。

    策略：**内容优先**，与 validate_skill.py 的红牌扫描保持一致——
    两个门的覆盖面必须相同，否则「红牌扫得到但残留扫不到」会变成盲区
    （实测曾出现：validate 侧靠可打印比例嗅探覆盖了无扩展名载体，
      self_check 侧仍靠扩展名白名单 → Dockerfile 里的残留完全漏检）。

    即：**除明确排除的之外，所有文件都扫**；二进制/超大文件跳过。
    """
    out = []
    for root, dirs, files in os.walk(PKG_ROOT):
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules'}]
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), PKG_ROOT).replace("\\", "/")
            if rel.startswith('.git/'):
                continue
            if rel in ACTIVE_FILES_EXCLUDE:
                continue
            full = os.path.join(PKG_ROOT, rel)
            try:
                if os.path.getsize(full) > 8 * 1024 * 1024:
                    continue  # 超大文件跳过，避免读取拖慢自检
                with open(full, "rb") as fh:
                    head = fh.read(4096)
            except OSError:
                continue
            if not head:
                continue
            # 二进制（magic bytes / NUL 占比高）跳过；其余一律纳入扫描
            if _looks_binary(head):
                continue
            out.append(rel)
    return sorted(out)


def _looks_binary(head):
    """粗判二进制：magic bytes 或 NUL 字节过多。"""
    if head.startswith((b'\x7fELF', b'MZ', b'PK\x03\x04', b'\x1f\x8b', b'BZh')):
        return True
    if head.count(b'\x00') > len(head) * 0.05:
        return True
    return False


def check_frontmatter():
    path = os.path.join(PKG_ROOT, "SKILL.md")
    text = read_text(path)
    # 复用共享解析器（scripts/_common.py）——避免两套 frontmatter 解析器规则漂移
    data, err = parse_frontmatter(text)
    if err:
        return False, [err]
    problems = []
    for key in ("name", "description", "metadata"):
        if key not in data:
            problems.append(f"frontmatter 缺少 {key}")
    if isinstance(data.get("metadata"), dict) and "version" not in data["metadata"]:
        problems.append("metadata 缺少 version")
    desc = data.get("description", "")
    if not desc:
        problems.append("description 为空")
    if problems:
        return False, problems
    return True, [
        f"name={data['name']}",
        f"version={data['metadata']['version']}",
        f"description={len(desc)} 字符",
    ]


def check_reference_files():
    path = os.path.join(PKG_ROOT, "SKILL.md")
    text = read_text(path)
    # 提取 SKILL.md 中反引号包裹的路径引用（**任意扩展名**）。
    # 早期正则写死 `\.md`，于是 SKILL.md 里引用了 `references/x.yaml` 也不会被登记，
    # 反向死件检查就会把它误报为死件（M2 的另一半）。扩展名不再设限。
    # 注意：并非所有引用都是本包文件——协议里也会提到**目标 skill 侧工作目录**的文件
    # （如 improve 协议的 baseline.md、evolution-log.md）。这些不属于本包，不能判为缺失。
    # 判定规则：只校验「以包内目录前缀开头」或「包根直属且真实存在的文件名」的引用；
    # 其余（裸文件名且不在包内）视为外部工作目录文件，跳过。
    all_refs = set(re.findall(r"`([\w][\w./-]*\.[A-Za-z0-9]{1,8})`", text))
    package_refs = set()
    for r in sorted(all_refs):
        if (r.startswith("references/") or r.startswith("evals/")
                or r.startswith("scripts/") or r.startswith("records/")
                or r.startswith("assets/")):
            package_refs.add(r)
        elif ("/" not in r) and os.path.exists(os.path.join(PKG_ROOT, r)):
            package_refs.add(r)  # 包根直属文件（SKILL.md / README.md / CHANGELOG.md）
    missing = []
    checked = []
    for r in sorted(package_refs):
        full = os.path.join(PKG_ROOT, r)
        if os.path.exists(full):
            checked.append(r)
        else:
            missing.append(r)
    # 反向检查：references/ 与 evals/ 下**每个实际文件**都必须被 SKILL.md 引用（防死件）。
    # ⚠️ 早期实现用 `if not fn.endswith(".md"): continue`，把非 markdown 交付物
    # （`.txt` 说明、`.yaml` 配置、`.json` 样例、图片等）整类跳过 —— 它们既进不了
    # 正向校验、也进不了反向死件检查，**完全隐形**（M2）。死件不看扩展名。
    # records/ 是**历史留档**（审查报告 / 评测卡），同样必须被引用，
    # 否则它就成了死件检查管不到的角落——新增目录不等于新增免责区。
    # ⚠️ 这四个目录**必须存在**，缺了要报错而不是跳过。
    # 实测踩过：整个 records/ 被误删后，这里 `if not isdir: continue` 直接跳过，
    # 反向检查一声不响 —— 结构目录消失是**包损坏**，不是"这个可选目录还没启用"。
    for sub in ("references", "evals", "records", "assets"):
        d = os.path.join(PKG_ROOT, sub)
        if not os.path.isdir(d):
            missing.append("%s/ 目录不存在 —— 它是本包的结构组成部分，被删了？" % sub)
            continue
        for root, _dirs, _files in os.walk(d):
            for fn in sorted(_files):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, PKG_ROOT).replace("\\", "/")
                if rel not in package_refs:
                    missing.append(rel + "（存在但未被 SKILL.md 引用 → 死件）")
    ok = len(missing) == 0
    return ok, (checked if ok else missing)


def check_test_prompts():
    path = os.path.join(PKG_ROOT, "test-prompts.json")
    if not os.path.exists(path):
        return False, ["test-prompts.json 不存在"]
    try:
        data = json.loads(read_text(path))
    except Exception as e:
        return False, [f"JSON 解析失败: {e}"]
    if not isinstance(data, list) or not data:
        return False, ["test-prompts.json 顶层应为非空数组"]
    problems = []
    valid_cmds = {"skill-create", "skill-improve", "skill-vet"}
    for item in data:
        cid = item.get("id", "?")
        cmd = item.get("command")
        if cmd not in valid_cmds:
            problems.append(f"#{cid}: command={cmd} 非法（应为 {valid_cmds}）")
            continue
        proto = os.path.join(PKG_ROOT, "references", f"{cmd}.md")
        if not os.path.exists(proto):
            problems.append(f"#{cid}: 子协议 references/{cmd}.md 缺失")
        for req in ("prompt", "expected", "mode"):
            if req not in item:
                problems.append(f"#{cid}: 缺少字段 {req}")
    ok = len(problems) == 0
    return ok, (data if ok else problems)


def check_residues():
    hits = []
    scanned = collect_active_files()
    for rel in scanned:
        full = os.path.join(PKG_ROOT, rel)
        # 二进制安全的读取：残留可能藏在 UTF-16 等编码里
        with open(full, "rb") as fh:
            raw = fh.read()
        texts = [raw.decode("utf-8", errors="ignore")]
        for enc in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                t = raw.decode(enc)
                # UTF-16 解码成功但内容几乎不可打印 → 多半是误判，跳过
                if t and sum(1 for c in t[:400] if c.isprintable() or c in "\r\n\t") > len(t[:400]) * 0.8:
                    texts.append(t)
            except Exception:
                pass
        for pat in FORBIDDEN_RESIDUES:
            for t in texts:
                for m in re.finditer(pat, t):
                    ctx = t[max(0, m.start() - 20): m.end() + 20].replace("\n", " ")
                    hits.append(f"{rel}: …{ctx}…")
    return len(hits) == 0, (hits if hits else "扫描 %d 个活跃文件，无残留" % len(scanned))


def check_tools():
    """确认 scripts/ 下的工具脚本存在（避免死件）。"""
    expected = ["scripts/_common.py", "scripts/self_check.py", "scripts/validate_skill.py"]
    missing = [t for t in expected if not os.path.exists(os.path.join(PKG_ROOT, t))]
    if missing:
        return False, missing
    return True, expected


def _make_clean_sample():
    """造一个干净的临时 skill 样本目录，用于实际调用校验器（返回其路径）。"""
    import tempfile
    d = os.path.join(tempfile.mkdtemp(prefix="lc-contract-"), "sample")
    os.makedirs(os.path.join(d, "evals"), exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: sample\ndescription: \"A sample. Use when testing.\"\n"
                "metadata:\n  version: \"0.1.0\"\n---\n# S\n## Protocol\n1. x\n"
                "## Anti-Patterns\n| a | b | c |\n")
    with open(os.path.join(d, "evals", "basic.md"), "w", encoding="utf-8") as f:
        f.write("## 场景1：a\n输入：x\n预期：y\n\n## 场景2：b\n输入：z\n预期：w\n")
    return d


def _run_script(script, *args):
    """实际调用脚本，返回 (exit_code, 合并输出)。用于「文档声明 ↔ 实现」的实际验证。"""
    import subprocess
    import sys as _sys
    try:
        p = subprocess.run([_sys.executable, script] + list(args),
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return -1, str(e)


def _probe_supported_modes(vpath, sample):
    """探明 validate_skill.py **实际支持**的 `--mode` 集合。

    做法：用一个必然非法的 mode 触发报错，从报错文案里解析支持清单。
    为什么不用源码常量：源码常量与实现会「一起」漂移（改了 if 忘了改常量），
    而报错文案是人照实现写的、且会被实际执行路径触发，更贴近**行为**。
    探针解析不出时退回源码解析，仍失败返回 None（由调用方报「探针失效」）。
    """
    _code, out = _run_script(vpath, sample, "--mode", "__probe__")
    mm = re.search(r"仅支持\s*([A-Za-z|,\s]+)", out or "")
    if mm:
        modes = {x.strip() for x in re.split(r"[|,\s]+", mm.group(1)) if x.strip()}
        if modes:
            return modes
    src = read_text(vpath)
    mm = re.search(r"if\s+mode\s+not\s+in\s*\(([^)]*)\)", src)
    if mm:
        return {x.strip().strip("\"'") for x in mm.group(1).split(",") if x.strip()}
    return None


def check_script_contract():
    """校验文档里声明的脚本调用与实际脚本能力一致（防文档漂移）。

    1. 文档中出现的 `<lifecycle>/scripts/xxx.py` 必须真实存在；
    2. 文档声明的 CLI 选项 / 模式必须被脚本实际支持，
       否则使用者会照文档敲出必然失败的命令。
    """
    problems = []
    doc_text = ""
    refs_dir = os.path.join(PKG_ROOT, "references")
    ref_files = []
    if os.path.isdir(refs_dir):
        ref_files = sorted(f for f in os.listdir(refs_dir) if f.endswith(".md"))
    for rel in ["SKILL.md", "README.md"] + ["references/" + f for f in ref_files]:
        p = os.path.join(PKG_ROOT, rel)
        if os.path.exists(p):
            doc_text += read_text(p)

    # 1) 文档引用的脚本路径必须存在
    for ref in sorted(set(re.findall(r"<lifecycle>/scripts/([\w.-]+\.py)", doc_text))):
        if not os.path.exists(os.path.join(PKG_ROOT, "scripts", ref)):
            problems.append("文档引用了不存在的脚本: <lifecycle>/scripts/%s" % ref)

    # 2) 文档声明的 CLI 能力必须被脚本**实际支持**——
    #    只比对源码字符串会漏（文档与实现同时写错、或实现改了名）。故实际调用验证。
    vpath = os.path.join(PKG_ROOT, "scripts", "validate_skill.py")
    if os.path.exists(vpath):
        # 用**临时的干净样本**做实际调用验证——
        # 不能对包自身跑（自身含红牌表与夹具，会被判 CRITICAL 而误报）。
        sample = _make_clean_sample()
        try:
            # ---- 反向验证：从**文档**枚举，再向**实现**求证 ----
            # ⚠️ 早期实现写死 `for mode in ("create","improve","vet")`，等于拿**实现**的
            # 模式清单去核对文档：文档若写了 `--mode approve`（实现根本不支持），
            # 循环里根本没这个值，检查立刻空转通过 —— 正向白名单式的自查等于没查（M3）。
            supported = _probe_supported_modes(vpath, sample)
            documented = set()
            for blob in re.findall(r"--mode[= ]([A-Za-z][\w|,-]*)", doc_text):
                for one in re.split(r"[|,]", blob):
                    if one.strip():
                        documented.add(one.strip())
            if supported:
                for mode in sorted(documented):
                    if mode not in supported:
                        problems.append(
                            "文档声明 --mode %s，但 validate_skill.py 仅支持 %s"
                            % (mode, "|".join(sorted(supported))))
                    else:
                        code, out = _run_script(vpath, sample, "--mode", mode)
                        # 声明为支持的模式若真的跑不起来，同样算契约破裂
                        if code == 2 and "仅支持" in out:
                            problems.append(
                                "文档提到 --mode %s，但 validate_skill.py 未实现该模式" % mode)
            elif documented:
                problems.append(
                    "无法探明 validate_skill.py 支持的 mode 集合"
                    "（探针失效，文档 → 实现的反向校验无从进行）")
            # ---- 选项层反向验证：文档提到的每个 `--xxx` 都必须被实现接受 ----
            # 早期只验了 --json 一个选项，`--seal` / `--verify-seal` 文档写了却从来
            # 没人核对；实现若删掉它们，检查仍全绿（与 M3 同一条病根：只验自己想到的）。
            # 判据用实现的「未知选项」报错，而不是另写一份选项白名单。
            #
            # ⚠️ 但 `--xxx` 不都是**我们的**选项。实测踩过：publish.md 里修「别用裸 cp -r」
            # 时写了 `tar --exclude=.git` / `rsync -a --exclude=...`，检查器把 `--exclude`
            # 当成本脚本的选项去求证，直接误报契约破裂（还连带 2 条测试变红）。
            # 判据：**外来命令块里的选项不归我们管** —— 一个代码块里出现
            # tar/rsync/git 这类命令、且块内没提我们的脚本，就整块跳过选项抽取。
            _FOREIGN = ("tar", "rsync", "git", "npm", "npx", "pip", "pip3", "docker",
                        "curl", "wget", "zip", "unzip", "7z", "robocopy", "chmod",
                        "find", "xargs", "sed", "awk", "grep", "ssh", "scp")
            _OURS = ("validate_skill.py", "self_check.py")
            _opt_text_parts, _in_fence, _buf = [], False, []
            for _ln in doc_text.splitlines():
                if _ln.strip().startswith("```"):
                    if _in_fence:                     # 围栏结束 → 判定整块是否收选项
                        _blk = "\n".join(_buf)
                        _has_ours = any(o in _blk for o in _OURS)
                        _has_foreign = any(
                            re.match(r"^\s*(?:\S*[/\\])?" + c + r"(?:\.exe)?\s", l)
                            for l in _buf for c in _FOREIGN)
                        if not _has_foreign or _has_ours:
                            _opt_text_parts.append(_blk)
                        _buf = []
                    _in_fence = not _in_fence
                    continue
                if _in_fence:
                    _buf.append(_ln)
                else:
                    _opt_text_parts.append(_ln)       # 正文照常抽
            _opt_text = "\n".join(_opt_text_parts)
            # 允许大写：否则 `--seal-BOGUS` 会被截成 `--seal-`，报错信息指错对象
            for opt in sorted(set(re.findall(r"(--[A-Za-z][A-Za-z0-9-]{2,})", _opt_text))):
                if opt == "--mode":
                    continue          # 上面已按**取值**校验过，这里不重复
                extra = ["probe"] if opt == "--verify-seal" else []
                _code, out = _run_script(vpath, sample, "--mode", "vet", opt, *extra)
                if "未知选项" in out:
                    problems.append(
                        "文档声明选项 %s，但 validate_skill.py 不识别该选项" % opt)
            if "--json" in doc_text:
                code, out = _run_script(vpath, sample, "--mode", "vet", "--json")
                if not out.strip().startswith("{"):
                    problems.append("文档提到 --json，但 validate_skill.py 未产出合法 JSON（退出码 %d）" % code)
            # --help 必须可用且退出码 0
            code, out = _run_script(vpath, "--help")
            if code != 0 or "用法" not in out:
                problems.append("validate_skill.py --help 不可用（退出码 %d）" % code)
        finally:
            import shutil as _sh
            _sh.rmtree(os.path.dirname(sample), ignore_errors=True)
    spath = os.path.join(PKG_ROOT, "scripts", "self_check.py")
    if os.path.exists(spath):
        # ⚠️ **不能调用自己**（self_check.py --json）——那会无限递归。
        # 改为静态检查：确认源码里确有 --json 分支与 json.dumps 输出。
        ssrc = read_text(spath)
        if "--json" in doc_text:
            if "--json" not in ssrc or "json.dumps" not in ssrc:
                problems.append("文档提到 self_check.py --json，但脚本未实现 JSON 输出")

    # 3) 共享模块必须被两个脚本都引用（防止 frontmatter 解析器再次分叉）
    cpath = os.path.join(PKG_ROOT, "scripts", "_common.py")
    if os.path.exists(cpath):
        for s in ("validate_skill.py", "self_check.py"):
            sp = os.path.join(PKG_ROOT, "scripts", s)
            if os.path.exists(sp) and "_common" not in read_text(sp):
                problems.append("scripts/%s 未复用 scripts/_common.py（解析器可能再次分叉）" % s)

    ok = len(problems) == 0
    return ok, (problems if problems else "文档声明的脚本路径与 CLI 选项均与实现一致")


def _checkbox_items(text, heading):
    """取指定标题下（到下一个同级或更高级标题为止）的 `- [ ]` 条目原文。

    必须按**小节切片**取，不能全文 grep —— skill-improve.md 的 CHECKPOINT 小节
    也有 `- [ ]` 条目（备份确认之类），全文提取会把它们混进来，比对必然误报。
    """
    pat = r"^#{1,6}\s*" + re.escape(heading) + r"[^\n]*\n(.*?)(?=^#{1,6}\s|\Z)"
    m = re.search(pat, text, re.M | re.S)
    if not m:
        return None
    return [ln.strip() for ln in m.group(1).splitlines()
            if ln.strip().startswith("- [ ]")]


def check_checklist_sync():
    """校验两份「同源检查清单」没有漂移。

    `references/improve-checklist.md` 开头明写：
      「下方「每轮改进前自检」与 skill-improve.md 的「思维检查清单」同源，
        改一处需同步另一处，避免漂移。」

    但这条约定**只靠注释维持** —— 写注释的人记得，下一个人未必。
    实测：本检查第一次跑就抓到一条真漂移（末尾条目一边少了半句）。
    约定写进注释 ≠ 会被执行，所以要有机器盯着。
    """
    pairs = (("references/skill-improve.md", "思维检查清单"),
             ("references/improve-checklist.md", "每轮改进前自检"))
    got = {}
    for rel, heading in pairs:
        p = os.path.join(PKG_ROOT, rel)
        if not os.path.exists(p):
            return False, ["%s 缺失" % rel]
        items = _checkbox_items(read_text(p), heading)
        if items is None:
            return False, ["%s 找不到「%s」小节（标题被改名了？）" % (rel, heading)]
        if not items:
            return False, ["%s 的「%s」小节里没有任何 `- [ ]` 条目" % (rel, heading)]
        got[rel] = items

    a, b = got[pairs[0][0]], got[pairs[1][0]]
    problems = []
    if len(a) != len(b):
        problems.append("条目数不一致：skill-improve.md %d 条 vs improve-checklist.md %d 条"
                        % (len(a), len(b)))
    for x in [i for i in a if i not in b]:
        problems.append("只在 skill-improve.md 出现：%s" % x)
    for x in [i for i in b if i not in a]:
        problems.append("只在 improve-checklist.md 出现：%s" % x)
    if problems:
        return False, problems
    return True, "两份检查清单同源（各 %d 条，逐条一致）" % len(a)


def check_cross_references():
    """检查包内**文档之间**的互相引用是否指向真实存在的文件。

    背景：此前只检查 SKILL.md → references/ 的引用，
    references/ 之间、以及 references/ → scripts/ 的悬空引用无人发现，
    而 agent 是按引用去 Read 的，悬空引用等于死链。

    覆盖两种引用写法：
      1) 反引号包裹： `references/xxx.md`
      2) markdown 链接： [说明](references/xxx.md)
    只扫 Markdown / JSON（人类与 agent 读的文档）：脚本源码里的字符串字面量
    （如测试用例中故意构造的悬空路径、正则模式定义）不是真实引用，不应误报。
    """
    problems = []
    for rel in collect_active_files():
        if not rel.endswith((".md", ".json")):
            continue
        full = os.path.join(PKG_ROOT, rel)
        text = read_text(full)
        # 反引号形式
        # ⚠️ 扩展名**不设限**：早期写死 `\.(?:md|py|json)`，于是 `references/x.yaml`
        # 这类悬空引用直接隐形（M2 的同一条病根：白名单=盲区）。
        # 前缀仍限定 references|scripts|evals，用于区分「包内路径」与普通行文。
        _PKG_REF = r"(?:references|scripts|evals|records|assets)/[\w./-]+\.[A-Za-z0-9]{1,8}"
        refs = set(re.findall(r"`(" + _PKG_REF + r")`", text))
        # markdown 链接形式 [text](path)
        refs |= set(re.findall(r"\]\(" + _PKG_REF + r"\)", text))
        for ref in sorted(refs):
            if not os.path.exists(os.path.join(PKG_ROOT, ref)):
                problems.append("%s 引用了不存在的文件: %s" % (rel, ref))

    # ---- 章节级引用：`xxx.md「某节」` 的「某节」必须真的是该文件的标题 ----
    # 实测踩过：6 份协议都写「见主入口 SKILL.md「路径约定」」，而 SKILL.md 里那只是
    # 一个引用块、没有标题；另有「见 skill-vet.md「判定门」」也是悬空的。
    # 文件存在 ≠ 章节存在 —— 死链比缺文件更隐蔽，因为路径检查是绿的。
    titles = {}
    target_files = ["SKILL.md", "README.md"]
    for sub in ("references",):
        d = os.path.join(PKG_ROOT, sub)
        if os.path.isdir(d):
            target_files += [sub + "/" + f for f in sorted(os.listdir(d)) if f.endswith(".md")]
    for rel_t in target_files:
        p_t = os.path.join(PKG_ROOT, rel_t)
        if os.path.exists(p_t):
            titles[rel_t] = set(re.findall(r"^#{1,6}\s+(.+?)\s*$", read_text(p_t), re.M))
    for rel in collect_active_files():
        if not rel.endswith(".md"):
            continue
        text = read_text(os.path.join(PKG_ROOT, rel))
        # ⚠️ 文件名**常被反引号包住**（`` `skill-vet.md`「判定门」 ``），也可能带个「的」。
        # 早期正则只认裸的文件名紧跟「」，于是最常见的写法直接漏检 —— 注入测试时发现
        # 「检查是绿的但注入没被抓到」，即检查器自身假阴性。这里把反引号与「的」都放行。
        for m in re.finditer(r"([\w\-]+\.md)`?\s*(?:的)?\s*[「『]([^」』]{2,24})[」』]", text):
            fname, sec = m.group(1), m.group(2)
            target = fname if fname in ("SKILL.md", "README.md") else "references/" + fname
            if target not in titles:
                continue                      # 目标不是包内文档（如外部项目文件），不管
            if not any(sec in t for t in titles[target]):
                line = text[:m.start()].count("\n") + 1
                problems.append("%s:%d 引用 %s「%s」，但该文件没有这个标题（章节级死链）"
                                % (rel, line, fname, sec))

    ok = len(problems) == 0
    return ok, (problems if problems else "包内文档互相引用均指向真实文件与真实章节")


def check_redflag_sync():
    """检测红牌真源与各处投影是否漂移。

    真源：`scripts/redflags.py` 的 RED_FLAGS（每条有 RFxx 编号）。
    派生：`references/skill-vet.md`（协议正文）、`references/vet-checklist.md`（速查勾选版）、
          `assets/architecture.html`（架构图里的红牌矩阵）。

    做法：**按编号集合全等比对**——真源里的每个编号，各处都必须出现；
    各处出现的编号，也都必须在真源里。
    早期版本用「关键词是否两边都出现」来判定，既漏（关键词换了就失效）又误报。

    ⚠️ 架构图为什么也要纳入：它把 21 条红牌**逐条列了一遍**，那份清单就是第三份副本。
    不校验的话，将来加一条红牌而忘了同步，架构图会安静地展示一份过期的红牌矩阵 ——
    和「文档说 A、实现做 B」是同一类病。**凡是同一语义的第二个表达点，都要问是否同源投影。**
    """
    problems = []
    try:
        sys.path.insert(0, os.path.join(PKG_ROOT, "scripts"))
        from redflags import RED_FLAGS
        src_ids = set(rf["id"] for rf in RED_FLAGS)
        src_count = len(RED_FLAGS)
    except Exception as e:
        return False, ["无法导入红牌真源 scripts/redflags.py: %s" % e]

    projections = (("skill-vet.md", "references/skill-vet.md"),
                   ("vet-checklist.md", "references/vet-checklist.md"),
                   ("architecture.html", "assets/architecture.html"))
    for label, rel in projections:
        p = os.path.join(PKG_ROOT, rel)
        if not os.path.exists(p):
            problems.append("%s 缺失" % rel)
            continue
        text = read_text(p)
        doc_ids = set(re.findall(r"\bRF\d{2}\b", text))
        missing = sorted(src_ids - doc_ids)
        extra = sorted(doc_ids - src_ids)
        if missing:
            problems.append("%s 缺少红牌编号: %s（真源已定义但此处未列出 → 漂移）"
                            % (label, ", ".join(missing)))
        if extra:
            problems.append("%s 出现真源没有的红牌编号: %s（漂移或真源未更新）"
                            % (label, ", ".join(extra)))

    # 架构图额外核对「总条数」：它把数字直接写给读者看（KPI + 分组计数），
    # 编号集合相等但总数写错一样是在骗人。
    ap = os.path.join(PKG_ROOT, "references", "architecture.html")
    if os.path.exists(ap):
        m = re.search(r'<div class="kpi"><b>(\d+)</b><span>红牌</span>', read_text(ap))
        if not m:
            problems.append("architecture.html 找不到「红牌总数」KPI 标记（结构被改动了？）")
        elif int(m.group(1)) != src_count:
            problems.append("architecture.html 声明的红牌总数 %s ≠ 真源 %d 条"
                            % (m.group(1), src_count))

    # 指令层红牌：两份协议文档都必须有（防止新增后忘记同步）
    for label, rel in (("skill-vet.md", "references/skill-vet.md"),
                       ("vet-checklist.md", "references/vet-checklist.md")):
        p = os.path.join(PKG_ROOT, rel)
        if os.path.exists(p) and "指令层红牌" not in read_text(p):
            problems.append("%s 缺少「指令层红牌」小节（纯文本 skill 的主要风险面）" % label)

    ok = len(problems) == 0
    return ok, (problems if problems else
                "红牌编号集合与真源全等（%d 条），三处投影一致（协议 / 速查 / 架构图）" % len(src_ids))


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print("用法:\n"
              "  python scripts/self_check.py          # 人类可读报告\n"
              "  python scripts/self_check.py --json   # JSON 报告（可接入 CI）\n"
              "  python scripts/self_check.py --help   # 显示本帮助\n\n"
              "退出码: 0 = 全部通过, 1 = 存在失败项")
        sys.exit(0)
    as_json = "--json" in sys.argv
    results = {}

    f_ok, f_msg = check_frontmatter()
    results["frontmatter"] = {"ok": f_ok, "detail": f_msg}

    r_ok, r_msg = check_reference_files()
    results["reference_files"] = {"ok": r_ok, "detail": r_msg}

    t_ok, t_msg = check_test_prompts()
    results["test_prompts"] = {
        "ok": t_ok,
        "detail": (f"{len(t_msg)} 条场景，全部路由到子协议" if t_ok else t_msg),
    }

    s_ok, s_msg = check_residues()
    results["no_claude_residue"] = {"ok": s_ok, "detail": (s_msg if not s_ok else s_msg)}

    tools_ok, tools_msg = check_tools()
    results["tools"] = {"ok": tools_ok, "detail": (tools_msg if not tools_ok else "脚本齐全")}

    contract_ok, contract_msg = check_script_contract()
    results["script_contract"] = {"ok": contract_ok, "detail": contract_msg}

    rf_ok, rf_msg = check_redflag_sync()
    results["redflag_sync"] = {"ok": rf_ok, "detail": rf_msg}

    cl_ok, cl_msg = check_checklist_sync()
    results["checklist_sync"] = {"ok": cl_ok, "detail": cl_msg}

    xr_ok, xr_msg = check_cross_references()
    results["cross_references"] = {"ok": xr_ok, "detail": xr_msg}

    all_ok = all(v["ok"] for v in results.values())

    if as_json:
        print(json.dumps({"pass": all_ok, "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"skill-lifecycle-z 自检  (包根: {PKG_ROOT})\n" + "=" * 56)
        labels = {
            "frontmatter": "1. SKILL.md frontmatter 合法",
            "reference_files": "2. Reference Files 表文件齐全（双向）",
            "test_prompts": "3. test-prompts.json 可路由",
            "no_claude_residue": "4. 无 Claude Code 生态残留",
            "tools": "5. scripts/ 工具脚本齐全",
            "script_contract": "6. 文档脚本调用与实现一致",
            "redflag_sync": "7. 红牌清单三处一致",
            "checklist_sync": "8. 同源检查清单一致",
            "cross_references": "9. 包内互相引用无悬空",
        }
        for k, v in results.items():
            mark = "✅ PASS" if v["ok"] else "❌ FAIL"
            print(f"  [{mark}] {labels[k]}")
            if isinstance(v["detail"], list):
                for d in v["detail"]:
                    print(f"           - {d}")
            else:
                print(f"           {v['detail']}")
        print("=" * 56)
        print(f"  总结果: {'✅ 全部通过' if all_ok else '❌ 存在失败项'}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
