"""补全 extra_story_data_list.story_event 到全部 460 集，state 全 1。"""
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


def main() -> int:
    # 活动剧情的 episode_id 全集（从 master 的 id 列）
    c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
    all_ids = [r[0] for r in c.execute("SELECT id FROM story_event_story_data ORDER BY id")]
    print(f"master episode_id: {len(all_ids)} 个 (max={max(all_ids)})")

    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if "load_index" in os.path.basename(f)]
    f = max(cands, key=os.path.getmtime)
    raw = open(f, "rb").read()
    print(f"源: {os.path.basename(f)} ({len(raw)} B)")

    v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    d = v["data"]
    ex = d.get("extra_story_data_list", {})
    cur = ex.get("story_event", [])
    print(f"现有 story_event: {len(cur)} 条")

    tmpl = {x["episode_id"]: x for x in cur if isinstance(x, dict) and "episode_id" in x}
    new_arr = []
    for eid in all_ids:
        it = tmpl.get(eid, {"episode_id": eid, "state": 1})
        it["state"] = 1
        new_arr.append(it)

    ex["story_event"] = new_arr
    d["extra_story_data_list"] = ex
    print(f"新 story_event: {len(new_arr)} 条（全部 state=1）")

    new = msgpack.packb(v, use_bin_type=True)
    print(f"重编码: {len(raw)} -> {len(new)} B")

    # 替换 replay.bin
    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        data = b[off:off + dl]
        off += dl
        if 1_200_000 < decl < 1_300_000:
            try:
                vv = msgpack.unpackb(data, raw=False, strict_map_key=False)
                if isinstance(vv, dict) and "coin_info" in vv.get("data", {}):
                    continue
            except Exception:
                pass
        items[decl] = data
    items[len(new)] = new

    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["load/index"] = len(new)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print(f"path_declared load/index = {len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
