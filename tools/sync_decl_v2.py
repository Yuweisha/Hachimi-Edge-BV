"""从 raw/*.raw + 服务器日志的真实 POST 路径，重建 path_declared。

raw 文件名是 rel.replace("/", "_")，有歧义；
日志里有完整的 "POST /umamusume//////////<真路径>"，用它当字典。
"""
from __future__ import annotations

import base64
import json
import re
import struct
import sys
from pathlib import Path

RAW = Path(r"C:/Users/Schwarz/uma_replay/raw")
REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
LOCKED = Path(r"C:/Users/Schwarz/uma_replay/locked_paths.json")
LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:/Users/Schwarz/localsrv.log")

POST_PAT = re.compile(r"POST /umamusume/+([a-z0-9_/]+)")


def load_lib() -> dict[int, bytes]:
    b = REPLAY.read_bytes()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    out = {}
    for _ in range(n):
        a, d, dl = struct.unpack_from("<III", b, off)
        off += 12
        out[d] = b[off:off + dl]
        off += dl
    return out


def main() -> int:
    lib = load_lib()
    locked = set()
    if LOCKED.exists():
        try:
            data = json.loads(LOCKED.read_text(encoding="utf-8"))
            if isinstance(data, list):
                locked = set(data)
        except Exception:
            pass

    # 真实路径集合（来自日志）
    txt = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
    real_paths = sorted(set(POST_PAT.findall(txt)))
    print(f"日志里的真实路径: {len(real_paths)} 个")

    # 建索引：路径 → 文件名键（"/"→"_"）
    by_key = {}
    for p in real_paths:
        by_key[p.replace("/", "_")] = p
    # 已知 path_declared 里的路径也加进来
    cur = json.loads(DECL.read_text(encoding="utf-8")) if DECL.exists() else {}
    for p in cur:
        by_key.setdefault(p.replace("/", "_"), p)

    found = {}
    unknown = []
    for f in sorted(RAW.glob("*.raw")):
        stem = f.stem
        api = by_key.get(stem)
        if api is None:
            unknown.append(stem)
            continue
        try:
            b64 = f.read_bytes().strip()
            pad = b"=" * ((-len(b64)) % 4)
            raw = base64.b64decode(b64 + pad)
        except Exception:
            continue
        if len(raw) < 4:
            continue
        decl = struct.unpack_from("<I", raw, 0)[0]
        if decl == 0:
            key = -(len(raw) - 36)
            probe = len(raw) - 36
            note = f"不压缩 {probe}"
        else:
            key = decl
            probe = decl
            note = f"压缩 {decl}"
        found[api] = (key, note, probe in lib)

    print(f"匹配到 {len(found)} 个路径")
    if unknown:
        print(f"未匹配 {len(unknown)} 个文件名: {unknown[:8]}")

    missing = [(p, n) for p, (k, n, ok) in found.items() if not ok]
    if missing:
        print(f"\n库中缺 {len(missing)} 个:")
        for p, n in missing:
            print(f"  {p:<44} {n}")

    added = changed = 0
    for api, (key, note, ok) in sorted(found.items()):
        if api in locked:
            continue
        if api not in cur:
            cur[api] = key
            added += 1
        elif cur[api] != key:
            cur[api] = key
            changed += 1
    DECL.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\npath_declared: {len(cur)} 条（新增 {added}，更新 {changed}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
