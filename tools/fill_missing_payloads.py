"""把 path_declared 里指向、但 replay.bin 里缺失的明文补进去（从会话目录按长度找）。"""
from __future__ import annotations

import glob
import json
import os
import shutil
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
LOCKED = Path(r"C:/Users/Schwarz/uma_replay/locked_paths.json")
GD = Path(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn")


def main() -> int:
    b = REPLAY.read_bytes()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl
    print(f"replay.bin: {len(items)} 个 declared")

    cur = json.loads(DECL.read_text(encoding="utf-8"))
    locked = set()
    if LOCKED.exists():
        try:
            d = json.loads(LOCKED.read_text(encoding="utf-8"))
            if isinstance(d, list):
                locked = set(d)
        except Exception:
            pass

    # 需要的明文长度
    want = set()
    for api, key in cur.items():
        if api in locked:
            continue
        want.add(abs(key) if key < 0 else key)
    have = set(items)
    missing = sorted(want - have)
    print(f"缺失 {len(missing)} 个长度: {missing}")

    # 扫所有会话目录
    sessions = sorted(glob.glob(str(GD / "hachimi" / "http" / "*")), key=os.path.getmtime, reverse=True)
    print(f"扫描 {len(sessions)} 个会话目录")

    found = {}
    for sess in sessions:
        for f in glob.glob(os.path.join(sess, "*.msgpack")):
            sz = os.path.getsize(f)
            if sz in missing and sz not in found:
                found[sz] = f
        if len(found) == len(missing):
            break

    print(f"找到 {len(found)}/{len(missing)}")
    if len(found) < len(missing):
        lost = [x for x in missing if x not in found]
        print(f"  找不到: {lost}")

    shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_fill"))
    added = 0
    for sz, f in found.items():
        data = Path(f).read_bytes()
        try:
            msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        except Exception as e:
            print(f"  {sz}: msgpack 解不开 ({e})，跳过")
            continue
        items[sz] = data
        added += 1
        print(f"  + {sz:>8}  {os.path.basename(os.path.dirname(f))}/{os.path.basename(f)}")

    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for d, data in sorted(items.items()):
        out += struct.pack("<III", d, d, len(data)) + data
    REPLAY.write_bytes(out)
    print(f"\nreplay.bin: {len(items)} 条, {len(out)} B（新增 {added}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
