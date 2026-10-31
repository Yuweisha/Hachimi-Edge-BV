"""从 Il2CppDumper 的 dump.cs 里查比赛相关的类定义。

用法：
    python query_dump.py RaceSimulate
    python query_dump.py RaceHorseManager --all
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DUMP_CANDIDATES = [
    Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/il2cpp_out4/dump.cs"),
    Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/il2cpp_out3/dump.cs"),
    Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/il2cpp_out2/dump.cs"),
]


def find_dump() -> Path:
    for p in DUMP_CANDIDATES:
        if p.exists() and p.stat().st_size > 1000:
            return p
    # 兜底：在整个 docs 下找
    for p in Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs").rglob("dump.cs"):
        if p.stat().st_size > 1000:
            return p
    raise SystemExit("找不到 dump.cs，dump 还没成功")


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "RaceSimulate"
    show_all = "--all" in sys.argv

    dump = find_dump()
    print(f"使用 {dump}  ({dump.stat().st_size:,} B)")
    text = dump.read_text(encoding="utf-8", errors="replace")

    # 找所有 class/struct 定义行 + 它们的成员块
    pat = re.compile(
        r"(?:// Namespace: ([^\n]*)\n)?"
        r"\s*(?:\[[^\]]*\]\s*)*"
        r"(?:public|internal|private)?\s*(?:sealed\s+|abstract\s+|static\s+)*"
        r"(class|struct|enum|interface)\s+(\w+)[^\n{]*\n\{",
        re.M)

    hits = []
    for m in pat.finditer(text):
        ns = (m.group(1) or "").strip()
        kind, name = m.group(2), m.group(3)
        if key.lower() not in name.lower():
            continue
        # 取到匹配的右括号
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i+1]
        hits.append((ns, kind, name, body, m.start()))

    print(f"\n匹配 '{key}' 的类/结构：{len(hits)} 个")
    for ns, kind, name, body, offset in hits:
        print(f"\n{'='*78}")
        print(f"{kind} {ns + '.' if ns else ''}{name}   (at 0x{offset:x})")
        print(f"  成员数: {body.count(chr(10))}")
        if show_all or len(hits) <= 4:
            print(body[:4000])
        else:
            # 只打印字段部分（第一个方法之前）
            lines = body.split("\n")
            out = []
            for ln in lines:
                if re.search(r"\b(public|private|internal|protected)\s+[\w<>\[\],. ]+\s+\w+\s*[;{]", ln) and "(" not in ln:
                    out.append(ln)
                elif "//" in ln and "Offset" in ln:
                    out.append(ln)
                if len(out) > 40:
                    break
            print("\n".join(out) if out else "（无字段）")


if __name__ == "__main__":
    main()
