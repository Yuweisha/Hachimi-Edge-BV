"""同时解锁 load/index 和 read_info/index 里的所有故事。

加入：
  - home_story_data_array 的 id
  - story_event_story_data 的 story_id_1 / story_id_2（活动剧情，900xxxxx）
  - 保留原有 released 条目
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

LOAD_LEN = 1213518      # load/index
READ_LEN = 60361        # read_info/index


def collect_story_ids() -> set[int]:
    ids: set[int] = set()
    try:
        c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
        for a, b in c.execute("SELECT story_id_1, story_id_2 FROM story_event_story_data"):
            if a:
                ids.add(a)
            if b:
                ids.add(b)
        print(f"master story_id: {len(ids)}")
    except Exception as e:
        print("master 读取失败:", e)
    return ids


def unlock(raw: bytes, extra: set[int]) -> bytes:
    v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    d = v["data"]
    rel = d.get("released_episode_data_array")
    if rel is None:
        return raw

    have = {x["id"] for x in rel}
    want = set(have) | extra
    for x in d.get("home_story_data_array", []):
        want.add(x["id"])

    tmpl = {x["id"]: x for x in rel}
    merged = sorted(want)
    d["released_episode_data_array"] = [tmpl.get(i, {"id": i}) for i in merged]

    # 主线/角色故事 state 全置 1
    for k in ("main_story_data_list", "character_story_data_list"):
        arr = d.get(k)
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict) and "state" in it:
                    it["state"] = 1

    print(f"  released: {len(have)} -> {len(merged)}")
    return msgpack.packb(v, use_bin_type=True)


def main() -> int:
    extra = collect_story_ids()

    # 1. load/index
    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if os.path.getsize(f) == LOAD_LEN]
    load_raw = None
    if cands:
        f = max(cands, key=os.path.getmtime)
        print("load/index:", os.path.basename(f))
        load_raw = open(f, "rb").read()
        new_load = unlock(load_raw, extra)
        print(f"  {len(load_raw)} -> {len(new_load)} B")
    else:
        new_load = None
        print("load/index: 未找到")

    # 2. read_info/index
    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if os.path.getsize(f) == READ_LEN]
    read_raw = None
    if cands:
        f = max(cands, key=os.path.getmtime)
        print("read_info/index:", os.path.basename(f))
        read_raw = open(f, "rb").read()
        new_read = unlock(read_raw, extra)
        print(f"  {len(read_raw)} -> {len(new_read)} B")
    else:
        new_read = None
        print("read_info/index: 未找到")

    # 3. 合并进 replay.bin
    blob = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", blob, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        src, decl, dl = struct.unpack_from("<III", blob, off)
        off += 12
        data = blob[off:off + dl]
        off += dl
        if new_load is not None and decl == LOAD_LEN:
            data, decl = new_load, len(new_load)
        elif new_read is not None and decl == READ_LEN:
            data, decl = new_read, len(new_read)
        items[decl] = data
    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")

    # 4. path_declared
    m = json.load(open(DECL, encoding="utf-8"))
    if new_load is not None:
        m["load/index"] = len(new_load)
    if new_read is not None:
        m["read_info/index"] = len(new_read)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print("path_declared: load/index =", m.get("load/index"), ", read_info/index =", m.get("read_info/index"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
