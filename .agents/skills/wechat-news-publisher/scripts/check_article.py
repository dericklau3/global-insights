#!/usr/bin/env python3
"""Check a WeChat article against user-specific publishing conventions.

Usage: python3 scripts/check_article.py path/to/article.md [another.md ...]

Only uses the Python standard library. Does not validate news facts, images themselves,
licenses, or the quality/accuracy of the headline.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path


def lint(path: Path) -> list[str]:
    problems: list[str] = []
    if not path.is_file():
        return ["文件不存在"]
    s = path.read_text(encoding="utf-8")
    lines = s.splitlines()
    if not lines or not re.match(r"^# \S", lines[0]):
        problems.append("文章第一行应为单个 Markdown # 标题")

    # Only reject boilerplate top blocks, not natural mention of an event date in body.
    opening = "\n".join(lines[:7])
    if re.search(r"^\s*>\s+", opening, re.M):
        problems.append("文章开头有引用式导语（灰色引用框）")
    if re.search(r"^\s*(?:AI 前沿|科技产品)\s*(?:[｜|/]|$)", opening, re.M):
        problems.append("正文开头有栏目标签")
    if "AI 前沿" in s:
        problems.append("正文出现禁用栏目词：AI 前沿")

    if re.search(r"^#{1,6}\s*(?:资料来源|参考资料|参考链接|编辑说明|写在最后)\s*$", s, re.M | re.I):
        problems.append("正文含不需要的尾部参考资料/说教标题")
    if re.search(r"^\*\*(?:资料来源|参考资料|参考链接|编辑说明|写在最后)\*\*\s*$", s, re.M):
        problems.append("正文含不需要的尾部参考资料/说教标题")
    if re.search(r"^\*?(?:编辑说明|本文资料来源|资料整理).*?(?:\*)?$", s, re.M):
        problems.append("正文中存在编辑说明或来源附记")

    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", s)
    for src in images:
        bare = src.strip().split()[0].strip("<>\"'")
        if "cover" in bare.lower() or "封面" in bare:
            problems.append(f"正文包含封面图片：{bare}")
        if not re.match(r"^(?:https?://|data:|/)", bare):
            img = (path.parent / bare).resolve()
            if not img.is_file():
                problems.append(f"配图相对路径不存在：{bare}")
    # Possible unintended footer: warn only if there is a reference-like ending.
    if re.search(r"\n---\s*\n\s*(?:\*\*资料来源|#{1,6}\s*资料来源)", s):
        problems.append("文章尾部出现参考资料附录")
    if re.search(r"^##\s*[0-9０-９]{2}[｜.、]", s, re.M):
        problems.append("小标题出现密集编号形式，优先采用自然小标题")
    return problems


def main() -> int:
    if len(sys.argv) <= 1 or any(x in ("-h", "--help") for x in sys.argv[1:]):
        print(__doc__.strip())
        return 0 if len(sys.argv) > 1 else 2
    failed = False
    for arg in sys.argv[1:]:
        path = Path(arg).expanduser()
        p = lint(path)
        if p:
            failed = True
            print(f"[FAIL] {path}")
            for msg in p:
                print(f"  - {msg}")
        else:
            print(f"[PASS] {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
