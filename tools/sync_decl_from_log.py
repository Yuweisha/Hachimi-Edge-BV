"""从服务器日志同步 path_declared：日志里有 `proxy <path> -> declared=N` 就是真相。

用法：
  python tools/sync_decl_from_log.py [日志路径]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:/Users/Schwarz/localsrv.log")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")

PAT = re.compile(r"proxy ([a-z0-9_/]+) -> declared=(-?\d+)")


def main() -> int:
    if not LOG.exists():
        print(f"日志不存在: {LOG}")
        return 1
    txt = LOG.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for m in PAT.finditer(txt):
        path, decl = m.group(1), int(m.group(2))
        found[path] = decl
    if not found:
        print("日志里没有 proxy 记录")
        return 1
    print(f"日志里 {len(found)} 个不同接口")

    cur = json.loads(DECL.read_text(encoding="utf-8")) if DECL.exists() else {}

    # 锁定清单：这些路径永不被日志覆盖
    locked = set()
    try:
        lp = DECL.parent / "locked_paths.json"
        if lp.exists():
            data = json.loads(lp.read_text(encoding="utf-8"))
            if isinstance(data, list):
                locked = set(data)
                print(f"锁定路径: {sorted(locked)}")
    except Exception:
        pass
    print(f"当前 path_declared: {len(cur)} 条")

    # 清掉之前误加的文件名式键（含 __ 或明显不是路径的）
    bad = [k for k in cur if k not in found and (
        k.startswith("unknown/") or
        ("_" in k and "/" not in k)
    )]
    for k in bad:
        cur.pop(k)
        print(f"  删掉误加: {k}")

    added = changed = same = 0
    for path, decl in sorted(found.items()):
        if path in locked:
            print(f"  [锁定] {path} = {cur.get(path, '?')}（日志里的 {decl} 被忽略）")
            continue
        if path not in cur:
            cur[path] = decl
            added += 1
            print(f"  + {path} = {decl}")
        elif cur[path] != decl:
            print(f"  ~ {path}: {cur[path]} -> {decl}")
            cur[path] = decl
            changed += 1
        else:
            same += 1

    DECL.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果: {len(cur)} 条（新增 {added}，更新 {changed}，未变 {same}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
