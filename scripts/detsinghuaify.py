#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去清华化脚本 — 把「知识库条目/」订阅库清单从"清华专用"改写成机构无关的通用版本。

做什么：
  1. 剥离清华图书馆代理链：http(s)://tlink.lib.tsinghua.edu.cn/go?url=<真实URL> → <真实URL>
  2. 识别"校内本地镜像"URL（剥离代理后仍是 *.tsinghua.edu.cn 域名，无公开入口）→ 替换为中性提示
  3. 把「校外访问」整行替换为机构无关的说明
  4. 精确替换机构专有措辞：我馆/本馆/清华大学图书馆 → 订阅机构（不碰"清华简"等真实文献名）
  5. 生成变更报告，并把仍含"清华/tsinghua/校内"的残留处逐条列出，供人工复核

不做什么（安全起见交给人工）：
  - 不盲目替换"清华"二字（清华简 = 清华大学藏战国竹简，是真实文献名）
  - 不改写「适用场景/检索技巧」等正文的学术表述

输入： 知识库条目/*.md
输出： 知识库条目-通用版/*.md  +  scripts/detsinghuaify-report.md
原文件保留不动，便于 git diff 对照。
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "知识库条目"
OUT_DIR = REPO / "知识库条目-通用版"
REPORT = REPO / "scripts" / "detsinghuaify-report.md"

# 代理前缀：http(s)://tlink.lib.tsinghua.edu.cn/go?url=
PROXY_RE = re.compile(r"https?://tlink\.lib\.tsinghua\.edu\.cn/go\?url=")

# 校外访问整行（Markdown 列表项）
OFFCAMPUS_LINE_RE = re.compile(r"^- 校外访问：.*$", re.MULTILINE)
OFFCAMPUS_NEW = (
    "- 校外访问：本库为订阅型数据库。若你所在机构已订阅，"
    "通过机构图书馆的校外访问方式（VPN／反向代理／机构 SSO 等）登录即可；"
    "若未订阅，请参考「公开平台册」中的开放获取替代方案。"
)

# 访问入口整行
ACCESS_LINE_RE = re.compile(r"^- 访问入口：(.*)$", re.MULTILINE)

# 机构专有措辞（精确、安全）
PHRASE_SUBS = [
    ("清华大学图书馆", "订阅机构图书馆"),
    ("我校图书馆", "订阅机构图书馆"),
    ("我馆", "订阅机构"),
    ("本馆", "订阅机构"),
    ("校内IP", "机构内 IP"),
    ("校内 IP", "机构内 IP"),
]

# 残留检测（不自动改，仅报告）
RESIDUAL_PATTERNS = ["清华", "tsinghua", "校内", "校外访问控制系统", "智能网关", "MyLoft"]


def strip_proxy_and_flag_mirror(url: str):
    """剥离代理前缀；若真实URL仍是清华域名，判为本地镜像。返回 (清洗后文本, is_mirror)。"""
    cleaned = PROXY_RE.sub("", url).strip()
    if "tsinghua.edu.cn" in cleaned:
        return cleaned, True
    return cleaned, False


def process_text(text: str, stats: dict):
    # 1) 校外访问整行替换
    def _offcampus(_m):
        stats["offcampus_lines"] += 1
        return OFFCAMPUS_NEW
    text = OFFCAMPUS_LINE_RE.sub(_offcampus, text)

    # 2) 访问入口行：剥代理 + 镜像标注
    def _access(m):
        val = m.group(1).strip()
        cleaned, is_mirror = strip_proxy_and_flag_mirror(val)
        if is_mirror:
            stats["mirror_urls"] += 1
            return ("- 访问入口：（无公开入口：此为订阅机构本地镜像地址，"
                    "请按平台名检索其官方网站）")
        if cleaned != val:
            stats["access_stripped"] += 1
        return f"- 访问入口：{cleaned}"
    text = ACCESS_LINE_RE.sub(_access, text)

    # 3) 其余任意位置的代理链也一并剥离（特别提示/检索技巧里也可能出现）
    before = text
    text = PROXY_RE.sub("", text)
    if text != before:
        stats["inline_proxy_stripped"] += len(PROXY_RE.findall(before))

    # 4) 机构专有措辞精确替换
    for old, new in PHRASE_SUBS:
        cnt = text.count(old)
        if cnt:
            text = text.replace(old, new)
            stats["phrase_subs"][old] = stats["phrase_subs"].get(old, 0) + cnt

    return text


def scan_residuals(text: str):
    residuals = {}
    for pat in RESIDUAL_PATTERNS:
        lines = [
            (i + 1, ln.strip())
            for i, ln in enumerate(text.splitlines())
            if pat in ln
        ]
        if lines:
            residuals[pat] = lines
    return residuals


def main():
    if not SRC_DIR.is_dir():
        print(f"找不到源目录：{SRC_DIR}", file=sys.stderr)
        sys.exit(1)
    OUT_DIR.mkdir(exist_ok=True)

    files = sorted(SRC_DIR.glob("*.md"))
    report_lines = ["# 去清华化变更报告", "",
                    f"源目录：`知识库条目/`（{len(files)} 个文件）→ 输出：`知识库条目-通用版/`", ""]
    total = {
        "offcampus_lines": 0, "access_stripped": 0, "mirror_urls": 0,
        "inline_proxy_stripped": 0, "phrase_subs": {},
    }
    all_residuals = {}

    for f in files:
        text = f.read_text(encoding="utf-8")
        stats = {"offcampus_lines": 0, "access_stripped": 0, "mirror_urls": 0,
                 "inline_proxy_stripped": 0, "phrase_subs": {}}
        new_text = process_text(text, stats)
        (OUT_DIR / f.name).write_text(new_text, encoding="utf-8")

        # 汇总
        for k in ["offcampus_lines", "access_stripped", "mirror_urls", "inline_proxy_stripped"]:
            total[k] += stats[k]
        for k, v in stats["phrase_subs"].items():
            total["phrase_subs"][k] = total["phrase_subs"].get(k, 0) + v

        residuals = scan_residuals(new_text)
        if residuals:
            all_residuals[f.name] = residuals

        report_lines.append(
            f"- **{f.name}**：校外访问行 {stats['offcampus_lines']}，"
            f"访问入口去代理 {stats['access_stripped']}，本地镜像 {stats['mirror_urls']}，"
            f"正文内代理链 {stats['inline_proxy_stripped']}，"
            f"措辞替换 {sum(stats['phrase_subs'].values())}"
        )

    report_lines += ["", "## 总计", "",
                     f"- 校外访问整行替换：{total['offcampus_lines']}",
                     f"- 访问入口去代理：{total['access_stripped']}",
                     f"- 本地镜像（无公开入口，已标注）：{total['mirror_urls']}",
                     f"- 正文内代理链剥离：{total['inline_proxy_stripped']}",
                     "- 措辞替换："]
    for k, v in sorted(total["phrase_subs"].items(), key=lambda x: -x[1]):
        report_lines.append(f"  - `{k}` → 替换 {v} 处")

    report_lines += ["", "## 待人工复核的残留",
                     "（脚本刻意不自动改这些，避免误伤真实文献名如「清华简」）", ""]
    if not all_residuals:
        report_lines.append("无。")
    else:
        for fname, residuals in all_residuals.items():
            report_lines.append(f"### {fname}")
            for pat, lines in residuals.items():
                report_lines.append(f"- 含「{pat}」{len(lines)} 行：")
                for lineno, content in lines[:20]:
                    snippet = content[:120] + ("…" if len(content) > 120 else "")
                    report_lines.append(f"  - L{lineno}: {snippet}")
                if len(lines) > 20:
                    report_lines.append(f"  - …（另有 {len(lines) - 20} 行，略）")
            report_lines.append("")

    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print("完成。输出目录：", OUT_DIR)
    print("报告：", REPORT)
    print("总计：", {k: v for k, v in total.items() if k != "phrase_subs"})
    print("措辞替换：", total["phrase_subs"])


if __name__ == "__main__":
    main()
