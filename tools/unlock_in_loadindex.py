"""解锁 load/index 里的 released_episode_data_array。

同时处理 main_story_data_list / character_story_data_list / extra_story_data_list
里可能存在的解锁标记。
"""
from __future__ import annotations

import glob
import json
import os
import sqlite3
import struct
import sys

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
OLD_LEN = 1213518


def main() -> int:
    # 找 load/index
    found = []
    for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack")):
        if os.path.getsize(f) != OLD_LEN:
            continue
        found.append(f)
    if not found:
        print("找不到 load/index (len=%d)" % OLD_LEN)
        return 1
    f = max(found, key=os.path.getmtime)
    print("源:", os.path.basename(f))

    raw = open(f, "rb").read()
    v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    d = v["data"]

    rel = d.get("released_episode_data_array", [])
    have = {x["id"] for x in rel}
    print(f"原 released: {len(rel)}")

    want = set(have)
    for x in d.get("home_story_data_array", []):
        want.add(x["id"])
    try:
        c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
        for (eid,) in c.execute("SELECT DISTINCT episode_index_id FROM story_event_story_data"):
            want.add(eid)
    except Exception as e:
        print("master 读取失败:", e)

    tmpl = {x["id"]: x for x in rel}
    merged = sorted(want)
    d["released_episode_data_array"] = [tmpl.get(i, {"id": i}) for i in merged]
    print(f"新 released: {len(merged)}")

    # 顺带看其它故事容器
    for k in ("main_story_data_list", "character_story_data_list", "short_episode_data_array"):
        arr = d.get(k)
        if isinstance(arr, list) and arr and isinstance(arr[0], dict):
            print(f"  {k}: {len(arr)} 条, 键={list(arr[0].keys())[:6]}")

    out = msgpack.packb(v, use_bin_type=True)
    print(f"重编码: {len(raw)} -> {len(out)} B")

    # 合并进 replay.bin
    blob = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", blob, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        src, decl, dl = struct.unpack_from("<III", blob, off)
        off += 12
        data = blob[off:off + dl]
        off += dl
        if decl == OLD_LEN:
            data = out
            decl = len(out)
        items[decl] = data
    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["load/index"] = len(out)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print(f"path_declared: load/index -> {len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
