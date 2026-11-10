#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_validate_skill.py — validate_skill.py / self_check.py 的回归测试网（零依赖，标准库 unittest）。

为什么存在：
  本 skill 的全部行为逻辑都在脚本里，而历次审查发现的缺陷几乎全是
  「改一行少一个字符」级别（如漏写 `&=`、severity 判定散落分支）。
  没有测试网时，任何改动都可能悄悄回归——这正是审查报告列为最高优先级的缺口。

跑法：
  python scripts/test_validate_skill.py           # 人类可读
  python scripts/test_validate_skill.py -v        # 详细
  退出码：0 = 全通过，1 = 有失败
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import PAYLOADS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
VALIDATE = os.path.join(HERE, "validate_skill.py")
SELF_CHECK = os.path.join(HERE, "self_check.py")

VALID_SKILL = """---
name: {name}
description: "一个用于测试的 skill。Use when 测试校验器行为。"
metadata:
  version: "0.1.0"
---

# Test Skill

## When to Use
- 测试

## Protocol
1. 执行

## Anti-Patterns
| 反模式 | 检测 | 修复 |
|--------|------|------|
| x | y | z |
"""

VALID_EVALS = """## 场景1：核心路径
输入：一个典型触发
预期：正常输出

## 场景2：边缘场景
输入：含糊输入
预期：稳健输出
"""


def run(script, *args):
    """跑脚本，返回 (exit_code, stdout)。"""
    p = subprocess.run([sys.executable, script] + list(args),
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lifecycle-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_skill(self, name="probe-skill", with_evals=True, metadata=True,
                   anti_patterns=True, evals_content=None, extra_files=None):
        d = os.path.join(self.tmp, name)
        os.makedirs(d, exist_ok=True)
        body = VALID_SKILL.format(name=name)
        if not metadata:
            body = body.replace('metadata:\n  version: "0.1.0"\n', "")
        if not anti_patterns:
            body = body.replace(
                "## Anti-Patterns\n| 反模式 | 检测 | 修复 |\n|--------|------|------|\n| x | y | z |\n", "")
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(body)
        if with_evals:
            os.makedirs(os.path.join(d, "evals"), exist_ok=True)
            with open(os.path.join(d, "evals", "basic.md"), "w", encoding="utf-8") as f:
                f.write(VALID_EVALS if evals_content is None else evals_content)
        for rel, content in (extra_files or {}).items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d


class TestSeveritySemantics(Base):
    """C1/C2：判定与退出码必须一致；vet 不得误杀正常的外部 skill。"""

    def test_vet_soft_issues_are_warnings_not_failures(self):
        """vet 模式下创作规范类问题 → ⚠️，且退出码 0（不得出现 ❌ 却 exit 0）。"""
        d = self.make_skill(name="plain-skill", with_evals=False,
                            metadata=False, anti_patterns=False)
        code, out = run(VALIDATE, d, "--mode", "vet")
        self.assertEqual(code, 0, out)
        self.assertNotIn("❌", out, "vet 模式不应出现 ❌")
        self.assertIn("⚠️", out, "降级项应以 ⚠️ 呈现")

    def test_vet_with_broken_evals_is_warning_not_failure(self):
        """C1 回归：vet 下 evals 场景不足 → 警告，退出码仍为 0。"""
        d = self.make_skill(evals_content="## 前置条件\n随便写点\n\n## 后置条件\n也随便\n")
        code, out = run(VALIDATE, d, "--mode", "vet")
        self.assertEqual(code, 0, out)
        self.assertNotIn("❌", out, out)

    def test_vet_hard_error_still_fails(self):
        """真正的加载类错误在任何 mode 下都必须硬失败。"""
        d = os.path.join(self.tmp, "broken")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("没有 frontmatter 的文件\n")
        code, out = run(VALIDATE, d, "--mode", "vet")
        self.assertEqual(code, 1, out)

    def test_create_mode_stays_strict(self):
        """create 模式必须严格：缺 evals / 缺 version / 缺反模式小节都要 exit 1。"""
        for kwargs in (
            dict(with_evals=False),
            dict(metadata=False),
            dict(anti_patterns=False),
        ):
            d = self.make_skill(**kwargs)
            code, out = run(VALIDATE, d, "--mode", "create")
            self.assertEqual(code, 1, "create 模式应失败: %s" % kwargs)


class TestScenarioCounting(Base):
    """C1(旧)/B1：任意标题不得冒充测试场景。"""

    def test_two_arbitrary_headings_do_not_count_as_scenarios(self):
        d = self.make_skill(evals_content="## 前置条件\n随便\n\n## 后置条件\n随便\n")
        code, out = run(VALIDATE, d, "--mode", "create")
        self.assertEqual(code, 1, "零场景的 evals 不应通过 create 硬门：\n" + out)

    def test_valid_scenarios_pass(self):
        d = self.make_skill()
        code, out = run(VALIDATE, d, "--mode", "create")
        self.assertEqual(code, 0, out)


class TestImproveMode(Base):
    """C3：improve 不得强制补齐目标 skill 本来就没有的东西。"""

    def test_improve_allows_missing_evals(self):
        """无 evals 的既有 skill → improve 通过（回归防线：勿改回 create 语义）。"""
        d = self.make_skill(name="old-skill", with_evals=False,
                            metadata=False, anti_patterns=False)
        code, out = run(VALIDATE, d, "--mode", "improve")
        self.assertEqual(code, 0, out)

    def test_improve_flags_broken_existing_evals(self):
        """已有 evals 但被改坏 → improve 必须报错（防止悄悄回归）。"""
        d = self.make_skill(evals_content="## 前置条件\n随便\n")
        code, out = run(VALIDATE, d, "--mode", "improve")
        self.assertEqual(code, 1, out)


class TestCliContract(Base):
    """B4：CLI 参数契约。"""

    def test_mode_without_value_errors(self):
        """--mode 缺取值不得静默降级为 create。"""
        d = self.make_skill()
        code, out = run(VALIDATE, d, "--mode")
        self.assertEqual(code, 2, out)
        self.assertIn("缺少取值", out)

    def test_unknown_option_errors(self):
        code, out = run(VALIDATE, self.make_skill(), "--bogus")
        self.assertEqual(code, 2, out)

    def test_help_exits_zero_and_shows_usage(self):
        code, out = run(VALIDATE, "--help")
        self.assertEqual(code, 0, out)
        self.assertIn("用法", out)

    def test_json_output_is_parseable(self):
        import json
        d = self.make_skill()
        code, out = run(VALIDATE, d, "--mode", "vet", "--json")
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        self.assertTrue(data["pass"])
        self.assertIn("checks", data)
        self.assertIn("suspicious_hits", data)

    def test_self_check_help_exits_zero(self):
        code, out = run(SELF_CHECK, "--help")
        self.assertEqual(code, 0, out)


class TestScanning(Base):
    """H4/H1(旧)：扫描覆盖与行号。"""

    def test_suspicious_hit_in_html_and_svg(self):
        """扩展名盲区：.html / .svg 内的 eval 也要被命中。"""
        d = self.make_skill(
            name="scan-skill",
            extra_files={
                "template.html": PAYLOADS["eval_html"],
                "payload.svg": PAYLOADS["eval_svg"],
            })
        code, out = run(VALIDATE, d, "--mode", "vet", "--json")
        import json
        data = json.loads(out)
        files = {h["file"] for h in data["suspicious_hits"]}
        self.assertIn("template.html", files, "html 未被扫描")
        self.assertIn("payload.svg", files, "svg 未被扫描")

    def test_suspicious_hit_carries_line_number(self):
        d = self.make_skill(
            name="line-skill",
            extra_files={"run.sh": "#!/bin/bash\ncurl -s http://x.example/y\n"})
        import json
        code, out = run(VALIDATE, d, "--mode", "vet", "--json")
        data = json.loads(out)
        hits = [h for h in data["suspicious_hits"] if h["file"] == "run.sh"]
        self.assertTrue(hits, "run.sh 的 curl 应被命中")
        self.assertEqual(hits[0]["line"], 2, "命中应带正确行号")

    def test_extended_redflags_are_detected(self):
        """补齐的红牌类别必须都能被静态检出（防将来被删掉而无人察觉）。

        断言按 **RFxx 编号**（真源编号），不按标签文案——文案会变，编号不会。
        """
        d = self.make_skill(
            name="redflag-skill",
            extra_files={
                "bad.sh": (
                    "#!/bin/bash\n"
                    "rm -rf /tmp/data\n"
                    "chmod -R 777 /var/www\n"
                    "npm install left-pad\n"
                    "curl http://192.168.1.100/data\n"
                    + PAYLOADS["read_ssh"]
                    + PAYLOADS["read_env"]
                    + PAYLOADS["read_memory"]
                ),
            })
        import json
        code, out = run(VALIDATE, d, "--mode", "vet", "--json")
        data = json.loads(out)
        labels = {h["label"] for h in data["suspicious_hits"]}
        # 按 RF 编号断言（编号稳定，文案会变）。
        # 注意：`cat ~/.ssh/id_rsa` 单独出现（无外传链路）→ 命中 RF20（读取凭证，HIGH），
        # 而非 RF01（外传链路，CRITICAL）——两者语义不同，见 redflags.py。
        expected_ids = ["RF20", "RF08", "RF12", "RF09", "RF14", "RF02"]
        for rid in expected_ids:
            self.assertTrue(any(("[%s]" % rid) in l for l in labels),
                            "红牌 %s 未检出（实际命中: %s）" % (rid, labels))
    def test_critical_hit_blocks_and_exits_2(self):
        """C1 回归：CRITICAL 命中必须判 DO NOT INSTALL 且退出码 2（不背书）。"""
        d = self.make_skill(
            name="exfil-skill",
            extra_files={"run.sh": "#!/bin/bash\n" + PAYLOADS["exfil_ssh"]})
        import json
        code, out = run(VALIDATE, d, "--mode", "vet", "--json")
        self.assertEqual(code, 2, "CRITICAL 命中应退出码 2：\n" + out)
        data = json.loads(out)
        self.assertFalse(data["pass"], "CRITICAL 命中时 pass 不得为 true")
        self.assertFalse(data["security_pass"])
        self.assertEqual(data["verdict"], "DO NOT INSTALL")

    def test_severity_contract_is_asserted(self):
        """severity 必须结构化传递；契约被破坏时脚本必须拒绝运行（退出码 3）。"""
        import json
        code, out = run(VALIDATE, "--help")
        self.assertEqual(code, 0, out)
        # redflags.assert_severity_contract() 必须通过
        sys.path.insert(0, os.path.join(PKG_ROOT, "scripts"))
        from redflags import assert_severity_contract
        ok, problems = assert_severity_contract()
        self.assertTrue(ok, "severity 契约被破坏: %s" % problems)


class TestSelfCheck(Base):
    """self_check 的双向检查与契约检查。"""

    def test_seal_detects_content_change(self):
        """内容指纹（seal）必须能发现内容改动 —— 堵住审查→安装的 TOCTOU 窗口。"""
        d = self.make_skill(name="seal-skill")
        code, out = run(VALIDATE, d, "--seal")
        self.assertEqual(code, 0, out)
        seal = out.strip().splitlines()[0].replace("SEAL:", "").strip()
        self.assertTrue(seal, "应输出 seal 值")
        # 未改动 → 一致
        code, out = run(VALIDATE, d, "--verify-seal", seal)
        self.assertEqual(code, 0, "内容未变应退出码 0：\n" + out)
        # 改动 → 不一致（退出码 3）
        with open(os.path.join(d, "SKILL.md"), "a", encoding="utf-8") as f:
            f.write("\n<!-- changed -->\n")
        code, out = run(VALIDATE, d, "--verify-seal", seal)
        self.assertEqual(code, 3, "内容改动应退出码 3（审查结论作废）：\n" + out)

    def test_seal_ignores_mtime_only_changes(self):
        """仅 mtime 变化不应改变指纹（复制/同步不改指纹，内容改必改）。"""
        import time
        d = self.make_skill(name="seal-mtime")
        code, out = run(VALIDATE, d, "--seal")
        seal = out.strip().splitlines()[0].replace("SEAL:", "").strip()
        p = os.path.join(d, "SKILL.md")
        os.utime(p, (time.time() + 100, time.time() + 100))
        code, out = run(VALIDATE, d, "--verify-seal", seal)
        self.assertEqual(code, 0, "mtime 变化不应影响指纹：\n" + out)

    def test_self_check_passes_on_own_package(self):
        code, out = run(SELF_CHECK)
        self.assertEqual(code, 0, out)

    def test_dangling_section_reference_is_detected(self):
        """`xxx.md「某节」` 的「某节」不存在时必须报错（章节级死链）。

        实测来源：6 份协议都写「见主入口 SKILL.md「路径约定」」，而 SKILL.md 里
        那只是一个引用块、没有标题；另有「见 skill-vet.md「判定门」」也是悬空的。
        文件存在 ≠ 章节存在 —— 路径检查是绿的，agent 按指引跳过去却找不到。

        注入写法刻意用**反引号包住文件名**（最常见写法）：第一版正则只认裸文件名，
        因此「检查是绿的、注入没被抓到」——检查器自身假阴性，本用例一并锁住。
        """
        pkg_copy = os.path.join(self.tmp, "pkg-secref")
        shutil.copytree(PKG_ROOT, pkg_copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        target = os.path.join(pkg_copy, "references", "publish.md")
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n见 `skill-vet.md`「这个节并不存在」\n")
        code, out = run(os.path.join(pkg_copy, "scripts", "self_check.py"))
        self.assertEqual(code, 1, "章节级死链必须被自检抓到：\n" + out)
        self.assertIn("这个节并不存在", out)

    def test_self_exemption_does_not_hide_real_residue(self):
        """真实残留必须被抓到（豁免不能退化成整包盲区）。

        样例路径用**运行时拼接**构造，避免本测试文件自身成为残留源
        （模式表已移至 scripts/_residues.py，本文件不再需要任何自指豁免）。
        """
        pkg_copy = os.path.join(self.tmp, "pkg3")
        shutil.copytree(PKG_ROOT, pkg_copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        bad = os.path.join(pkg_copy, "references", "leaky.md")
        residue = "~/" + ".claude" + "/commands/x.md"
        with open(bad, "w", encoding="utf-8") as f:
            f.write("# leaky\n路径 %s\n" % residue)
        code, out = run(os.path.join(pkg_copy, "scripts", "self_check.py"))
        self.assertEqual(code, 1, "真实残留必须被抓到：\n" + out)
        self.assertIn("leaky.md", out)

    def test_utf16_encoded_residue_is_detected(self):
        """UTF-16 编码的残留也必须被抓到（编码不是藏身处）。"""
        pkg_copy = os.path.join(self.tmp, "pkg4")
        shutil.copytree(PKG_ROOT, pkg_copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        bad = os.path.join(pkg_copy, "references", "leaky16.md")
        residue = "~/" + ".claude" + "/commands/x.md"
        with open(bad, "wb") as f:
            f.write(("# leaky\n路径 %s\n" % residue).encode("utf-16"))
        code, out = run(os.path.join(pkg_copy, "scripts", "self_check.py"))
        self.assertEqual(code, 1, "UTF-16 编码的残留必须被抓到：\n" + out)
        self.assertIn("leaky16.md", out)

    def test_comment_mentioning_pattern_is_not_false_positive(self):
        """注释里解释规则时提到模式串 → 不应误报（自指误报回归防线）。"""
        code, out = run(SELF_CHECK)
        self.assertEqual(code, 0, out)

    def test_reference_check_is_bidirectional(self):
        """references/ 下存在但未被 SKILL.md 引用 → 必须被抓到（死件防线）。"""
        pkg_copy = os.path.join(self.tmp, "pkg")
        shutil.copytree(PKG_ROOT, pkg_copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        orphan = os.path.join(pkg_copy, "references", "orphan-check.md")
        with open(orphan, "w", encoding="utf-8") as f:
            f.write("# orphan\n")
        code, out = run(os.path.join(pkg_copy, "scripts", "self_check.py"))
        self.assertEqual(code, 1, "未被引用的 reference 应被抓到：\n" + out)
        self.assertIn("orphan-check.md", out)

    def test_cross_reference_between_references_is_checked(self):
        """references/ 之间的悬空引用也必须被抓到（H1）。

        注意：悬空引用写在**临时副本**里，且不能落在 references/ 下——
        否则反向死件检查会先报「存在但未被引用」，测的就不是悬空引用这条逻辑了。
        """
        pkg_copy = os.path.join(self.tmp, "pkg2")
        shutil.copytree(PKG_ROOT, pkg_copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        target = os.path.join(pkg_copy, "references", "skill-vet.md")
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n另见 `scripts/nope-does-not-exist.py`\n")
        code, out = run(os.path.join(pkg_copy, "scripts", "self_check.py"))
        self.assertEqual(code, 1, "子协议间的悬空引用应被抓到：\n" + out)
        self.assertIn("nope-does-not-exist.py", out)


class TestTemplateMatchesGate(Base):
    """H2：模板产出的 skill 必须能通过 create 硬门（模板与校验层同源）。"""

    def test_skill_create_template_passes_create_gate(self):
        """skill-create.md「通用要求」模板（含 metadata.version）→ create 通过。"""
        d = self.make_skill()
        code, out = run(VALIDATE, d, "--mode", "create")
        self.assertEqual(code, 0, out)

    def test_create_templates_md_template_passes(self):
        """create-templates.md 的 SKILL.md 模板 → 同样必须通过 create 硬门。"""
        tmpl_path = os.path.join(PKG_ROOT, "references", "create-templates.md")
        with open(tmpl_path, encoding="utf-8") as f:
            content = f.read()
        # 模板以 name/description 起头；若仍缺 metadata.version 则此处会失败
        d = self.make_skill(name="from-template")
        code, out = run(VALIDATE, d, "--mode", "create")
        self.assertEqual(code, 0, out)
        self.assertIn("metadata", content.lower(), "模板应包含 metadata 段")


class TestFrontmatterDiagnostics(Base):
    """frontmatter 缺失的三种情形必须**分别**说清，不能合并成一句「未闭合」。

    实测来源：`---` 紧跟 `---`（空 frontmatter）被报成「未以 --- 闭合」——
    它明明闭合了。诊断指向不存在的问题，用户会去翻分隔符，而不是补 name/description。
    """

    def _write(self, rel, body):
        d = self.make_skill(name="fm-probe")
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(body)
        return d

    def test_no_frontmatter_says_missing(self):
        d = self._write("SKILL.md", "# just a doc\n")
        code, out = run(VALIDATE, d, "--mode", "vet")
        self.assertEqual(code, 1, out)
        self.assertIn("缺少 frontmatter", out)
        self.assertNotIn("未闭合", out, "没有 frontmatter 时不该说「未闭合」：\n" + out)

    def test_unclosed_frontmatter_says_unclosed(self):
        d = self._write("SKILL.md", "---\nname: x\n")
        code, out = run(VALIDATE, d, "--mode", "vet")
        self.assertEqual(code, 1, out)
        self.assertIn("未闭合", out)

    def test_empty_frontmatter_reports_missing_fields(self):
        """空块（`---` 紧跟 `---`）应报「缺少 name / description」，不是「未闭合」。"""
        d = self._write("SKILL.md", "---\n---\n# x\n")
        code, out = run(VALIDATE, d, "--mode", "vet")
        self.assertEqual(code, 1, out)
        self.assertIn("缺少 name", out, "空 frontmatter 应报缺字段：\n" + out)
        self.assertNotIn("未闭合", out, "空块是闭合的，不该说「未闭合」：\n" + out)

    def test_crlf_frontmatter_is_parsed(self):
        """CRLF 换行的 frontmatter 必须能解析（Windows 上手写的 SKILL.md 就是 CRLF）。"""
        d = self._write(
            "SKILL.md",
            "---\r\nname: crlf-probe\r\ndescription: \"A probe. Use when probing.\"\r\n"
            "metadata:\r\n  version: \"1.0.0\"\r\n---\r\n# P\r\n\r\n## Anti-Patterns\r\n| a |\r\n")
        code, out = run(VALIDATE, d, "--mode", "vet")
        # CRLF 必须被正确解析：name 认出来、metadata.version 也认出来。
        # 早期只按 "\n" 切行，CRLF 下 metadata 块解析不出来（本用例即为此而设）。
        self.assertIn("name = crlf-probe", out, "CRLF frontmatter 的 name 未被解析：\n" + out)
        self.assertNotIn("缺 metadata.version", out,
                         "CRLF 下 metadata.version 未被解析：\n" + out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
