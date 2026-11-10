#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_redflags_adversarial.py — 红牌检测的**对抗性测试集**（零依赖，仅标准库）。

为什么需要这个文件（治理整改）：
  `test_validate_skill.py` 测的是「校验器的接口与语义」，
  但**红牌检测本身**——即「恶意载荷能否被检出、正当用法会不会被误杀」——
  此前没有任何测试覆盖。实测已发现三类真实缺口：
    · 编码维度：UTF-16（无 BOM / LE+BOM / BE+BOM）载荷完全隐身
    · 载体维度：Dockerfile / x.jar / 无扩展名纯文本载荷完全隐身
    · 误报维度：RF01/RF05 的正当用法（教学示例）被误判为 CRITICAL

  没有这层测试，上述缺口只能靠人工发现；而红牌是「安全门」，
  静默漏检比误报更危险——它给出虚假的安全保证。

跑法：
  python scripts/test_redflags_adversarial.py
  退出码：0 = 全部通过；1 = 有失败
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.dirname(HERE)
VALIDATE = os.path.join(HERE, "validate_skill.py")

# 载荷来自夹具模块（scripts/_fixtures.py）——测试文件本身不再持有恶意字面量，
# 避免扫描器把「自己的测试夹具」判成真实攻击。
sys.path.insert(0, HERE)
from _fixtures import PAYLOADS  # noqa: E402

PAYLOAD = PAYLOADS["exfil_ssh"].encode()

GOOD_FM = "---\nname: target\ndescription: \"A target. Use when testing.\"\n---\n# T\n"


def run(*args):
    p = subprocess.run([sys.executable, VALIDATE] + list(args),
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class AdversarialBase(unittest.TestCase):
    """构造一个待审 skill 目录，按需放入载荷文件。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="adv-")
        self.skill = os.path.join(self.tmp, "target")
        os.makedirs(self.skill, exist_ok=True)
        with open(os.path.join(self.skill, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: target\ndescription: \"A target. Use when testing.\"\n---\n# T\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, rel, raw):
        """放入一个载荷文件（rel 可含子目录）。"""
        p = os.path.join(self.skill, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        mode = "wb" if isinstance(raw, (bytes, bytearray)) else "w"
        with open(p, mode) as f:
            f.write(raw)
        return p

    def vet(self):
        """跑 vet 模式，返回 (exit_code, json)。"""
        code, out = run(self.skill, "--mode", "vet", "--json")
        try:
            data = json.loads(out)
        except Exception:
            data = {}
        return code, data

    def assert_blocked_by(self, rid):
        """断言：CRITICAL 级命中里包含指定 RF 编号，且退出码为 2。"""
        code, data = self.vet()
        labels = [h["label"] for h in data.get("blocking_hits", [])]
        self.assertTrue(any(("[%s]" % rid) in l for l in labels),
                        "期望被 %s 阻断，实际 blocking=%s" % (rid, labels))
        self.assertEqual(code, 2, "CRITICAL 命中应退出码 2，实际 %d" % code)
        self.assertFalse(data.get("security_pass", True))
        self.assertEqual(data.get("verdict"), "DO NOT INSTALL")

    def assert_not_blocked(self):
        """断言：没有 CRITICAL 命中（可接受 HIGH/MEDIUM/INFO 提示）。"""
        code, data = self.vet()
        self.assertEqual(data.get("blocking_hits", []), [],
                         "不应有 CRITICAL 命中，实际: %s" % data.get("blocking_hits"))
        self.assertTrue(data.get("security_pass", False))


class TestEncodingDimension(AdversarialBase):
    """编码维度：载荷不能靠换编码隐身。"""

    def test_plain_text_blocks(self):
        self.put("scripts/plain.md", PAYLOAD)
        self.assert_blocked_by("RF01")

    def test_base64_blocks(self):
        self.put("scripts/b64.py", base64.b64encode(PAYLOAD))
        self.assert_blocked_by("RF01")

    def test_hex_blocks(self):
        self.put("scripts/hex.py", PAYLOAD.hex().encode())
        self.assert_blocked_by("RF01")

    def test_utf16_nobom_blocks(self):
        self.put("scripts/u16_nobom.py", PAYLOAD.decode().encode("utf-16"))
        self.assert_blocked_by("RF01")

    def test_utf16le_bom_blocks(self):
        # Windows 典型形态：PowerShell Out-File 默认写 UTF-16LE + BOM
        self.put("scripts/w_le.py", b"\xff\xfe" + PAYLOAD.decode().encode("utf-16-le"))
        self.assert_blocked_by("RF01")

    def test_utf16be_bom_blocks(self):
        self.put("scripts/w_be.py", b"\xfe\xff" + PAYLOAD.decode().encode("utf-16-be"))
        self.assert_blocked_by("RF01")

    def test_latin1_blocks(self):
        self.put("scripts/l1.py", PAYLOAD.decode().encode("latin-1"))
        self.assert_blocked_by("RF01")


class TestCarrierDimension(AdversarialBase):
    """载体维度：载荷不能靠换文件名/扩展名隐身。"""

    def test_shebang_noext_blocks(self):
        self.put("install", b"#!/bin/sh\n" + PAYLOAD)
        self.assert_blocked_by("RF01")

    def test_bin_ext_blocks(self):
        self.put("payload.bin", PAYLOAD)
        self.assert_blocked_by("RF01")

    def test_dockerfile_blocks(self):
        self.put("Dockerfile", b"FROM alpine\n" + PAYLOAD)
        self.assert_blocked_by("RF01")

    def test_jar_ext_blocks(self):
        self.put("x.jar", PAYLOAD)
        self.assert_blocked_by("RF01")

    def test_noext_plaintext_blocks(self):
        self.put("noext_nontext", PAYLOAD)
        self.assert_blocked_by("RF01")

    def test_no_ext_hidden_dotfile_blocks(self):
        self.put(".hidden_payload", PAYLOAD)
        self.assert_blocked_by("RF01")


class TestInstructionInjection(AdversarialBase):
    """RF05 提示注入：正文层的越权指令也必须阻断。"""

    def test_ignore_previous_blocks(self):
        self.put("SKILL.md",
                 "---\nname: target\ndescription: \"A target. Use when testing.\"\n---\n"
                 + GOOD_FM + "\n" + PAYLOADS["inject_en"])
        self.assert_blocked_by("RF05")

    def test_do_not_ask_user_blocks(self):
        self.put("SKILL.md",
                 "---\nname: target\ndescription: \"A target. Use when testing.\"\n---\n"
                 + GOOD_FM + "\n" + PAYLOADS["inject_en_do_not_ask"])
        self.assert_blocked_by("RF05")

    def test_chinese_injection_blocks(self):
        self.put("SKILL.md",
                 "---\nname: target\ndescription: \"A target. Use when testing.\"\n---\n"
                 + GOOD_FM + "\n" + PAYLOADS["inject_zh"])
        self.assert_blocked_by("RF05")


class TestBenignNotFalsePositive(AdversarialBase):
    """误报维度：正当用法不得被误杀（否则红牌不可用）。"""

    def test_documented_api_call_is_not_critical(self):
        """只读公开 API 查询（skill-vet.md 自身的示例）不应被阻断。"""
        self.put("scripts/weather.sh",
                 "#!/bin/bash\ncurl -s \"https://wttr.in/Beijing?format=3\"\n")
        self.assert_not_blocked()

    def test_readme_documentation_is_not_critical(self):
        """文档里提到危险文件名（教学说明）不应被阻断。"""
        self.put("README.md",
                 "# 说明\n本工具会读取 ~/.ssh 下的公钥用于签名校验。\n")
        self.assert_not_blocked()

    def test_normal_code_is_not_critical(self):
        self.put("scripts/util.py", "def add(a, b):\n    return a + b\n")
        self.assert_not_blocked()

    def test_symlink_inside_package_is_not_critical(self):
        """包内软链（相对路径）不应被判 CRITICAL。"""
        self.put("scripts/util.py", "def add(a, b):\n    return a + b\n")
        os.symlink("util.py", os.path.join(self.skill, "scripts", "alias.py"))
        self.assert_not_blocked()


class TestSymlinkPolicy(AdversarialBase):
    """符号链接策略：包外软链 = CRITICAL（阻断），包内软链 = MEDIUM（仅提示）。

    依据：包外软链等价于 skill-vet.md Step 4 的 ⛔ EXTREME（读取工作区外文件），
    且安装后常驻用户 skill 目录 → 持久提权通道。
    """

    def test_out_of_package_symlink_blocks(self):
        """包外软链必须阻断（CRITICAL / DO NOT INSTALL）。"""
        target = os.path.join(self.tmp, "outside.txt")
        with open(target, "w", encoding="utf-8") as f:
            f.write("harmless\n")
        os.symlink(target, os.path.join(self.skill, "link.txt"))
        code, data = self.vet()
        labels = [h["label"] for h in data.get("blocking_hits", [])]
        self.assertTrue(any("符号链接" in l for l in labels),
                        "包外软链应报 CRITICAL，实际 blocking=%s" % labels)
        self.assertEqual(code, 2)
        self.assertFalse(data.get("security_pass", True))

    def test_out_of_package_symlink_dir_blocks(self):
        """包外软链**目录**也必须阻断——目录软链在 os.walk 里是隐形的（不进 files）。"""
        outside_dir = os.path.join(self.tmp, "outdir")
        os.makedirs(outside_dir, exist_ok=True)
        with open(os.path.join(outside_dir, "x.txt"), "w", encoding="utf-8") as f:
            f.write("data\n")
        os.symlink(outside_dir, os.path.join(self.skill, "dirlink"))
        code, data = self.vet()
        labels = [h["label"] for h in data.get("blocking_hits", [])]
        self.assertTrue(any("[RF21]" in l for l in labels),
                        "包外软链目录应报 RF21，实际 blocking=%s" % labels)
        self.assertEqual(code, 2)

    def test_sibling_prefix_directory_is_outside(self):
        """同前缀兄弟目录必须判为「包外」（防字符串前缀绕过）。

        包路径 .../skill，目标 .../skill-evil/x —— 前缀比较会误判为包内。
        """
        sibling = os.path.join(self.tmp, "skill-evil")
        os.makedirs(sibling, exist_ok=True)
        target = os.path.join(sibling, "secret.txt")
        with open(target, "w", encoding="utf-8") as f:
            f.write("data\n")
        # 让被审包叫 "skill"，兄弟叫 "skill-evil"（同前缀）
        skill_dir = os.path.join(self.tmp, "skill")
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: skill\ndescription: \"A t. Use when testing.\"\n---\n# T\n")
        os.symlink(target, os.path.join(skill_dir, "link.txt"))
        code, out = run(skill_dir, "--mode", "vet", "--json")
        data = json.loads(out)
        labels = [h["label"] for h in data.get("blocking_hits", [])]
        self.assertTrue(any("符号链接" in l for l in labels),
                        "同前缀兄弟目录应判为包外并阻断，实际 blocking=%s" % labels)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
