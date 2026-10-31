"""从服务器日志解析「路径 -> declared」，生成 path_declared.json。"""
from __future__ import annotations

import json
import re
import sys

LOG = r"C:/Users/Schwarz/localsrv.log"
OUT = r"C:/Users/Schwarz/uma_replay/path_declared.json"

pat = re.compile(r"proxy (\S+) -> declared=(\d+)")


def main() -> int:
    m = {}
    order = []
    try:
        lines = open(LOG, encoding="utf-8", errors="ignore").read().splitlines()
    except FileNotFoundError:
        print("日志不存在")
        return 1

    for line in lines:
        g = pat.search(line)
        if not g:
            continue
        path, decl = g.group(1), int(g.group(2))
        if path not in m:
            order.append(path)
        # 非 0 优先，同优先级取最新
        if decl > 0 or m.get(path, 0) == 0:
            m[path] = decl

    json.dump(m, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"写出 {OUT}，{len(m)} 条")
    for p in order:
        print("  %-44s %10d" % (p, m[p]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
