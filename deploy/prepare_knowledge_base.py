#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库导入准备 —— 把仓库里的知识库素材整理成一批可直接拖进 Dify 的文件。

做什么：
  - 汇集「公开平台册」(公开获取，人人可用) 与「知识库条目」(订阅型，需机构订阅)
  - 统一命名、加一行卷首说明(标明卷别，帮助检索时区分公开/订阅)
  - 输出到 deploy/dist/knowledge-base/，并生成 manifest.md 清单
  - 原文件不动

用法：
  python deploy/prepare_knowledge_base.py
然后在 Dify：知识库 → 创建 → 上传 deploy/dist/knowledge-base/ 下所有 .md
  → 选多语言 embedding(如 bge-m3) → 分段建议按 Markdown 标题(## 平台名)切片。
"""

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "deploy" / "dist" / "knowledge-base"

# (源目录, 输出前缀, 卷首说明)
SOURCES = [
    (REPO / "公开平台册", "公开平台",
     "> 卷别：公开获取平台（任何人可免费访问，无需机构订阅）。"),
    (REPO / "知识库条目", "订阅库",
     "> 卷别：订阅型数据库（需所在机构已订阅方可全文访问；未订阅请优先看「公开平台」卷）。"),
]


def clean_name(prefix: str, filename: str) -> str:
    """文件名形如 '德语区.md' → '公开平台_德语区.md' / '订阅库_德语区.md'。"""
    return f"{prefix}_{Path(filename).stem}.md"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    manifest = ["# 知识库导入清单", "",
                "在 Dify「知识库」里上传本目录下所有 .md；建议多语言 embedding + 按 `##` 标题分段。", ""]
    total = 0
    for src_dir, prefix, note in SOURCES:
        if not src_dir.is_dir():
            manifest.append(f"- ⚠️ 缺少源目录：`{src_dir.name}`")
            continue
        files = sorted(src_dir.glob("*.md"))
        manifest.append(f"## {prefix}（{len(files)} 份，源自 `{src_dir.name}/`）")
        for f in files:
            out_name = clean_name(prefix, f.name)
            text = f.read_text(encoding="utf-8")
            # 加卷首说明（若首行不是我们加过的）
            if not text.lstrip().startswith(">"):
                text = note + "\n\n" + text
            (OUT / out_name).write_text(text, encoding="utf-8")
            manifest.append(f"- `{out_name}`  ← {f.name}")
            total += 1
        manifest.append("")
    manifest.append(f"**合计 {total} 份文件。**")

    (OUT / "manifest.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"完成：{total} 份文件 → {OUT}")
    print(f"清单：{OUT / 'manifest.md'}")


if __name__ == "__main__":
    main()
