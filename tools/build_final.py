"""合成最终版 load/index：released=2121 + story_event=460 + card=89 + chara=76。

保持 card_list=89 与 note/index 的 release_card_array 风格一致（不引入角色/换装解锁，
避免 note/index 数据不一致导致笔记报错）。
"""
import glob
import json
import os
import shutil
import sqlite3
import struct
import sys

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
BASE_DECL = 1218759     # story_event=460 的基础


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_final")

    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    raw = items[BASE_DECL]
    v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    d = v["data"]
    print(f"基础: {BASE_DECL}, card={len(d['card_list'])}, chara={len(d['chara_list'])}, "
          f"released={len(d['released_episode_data_array'])}, "
          f"story_event={len(d['extra_story_data_list']['story_event'])}")

    # 1. released 补到 2121（主页故事 + 活动 story_id）
    c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
    extra = set()
    for a, bb in c.execute("SELECT story_id_1, story_id_2 FROM story_event_story_data"):
        if a:
            extra.add(a)
        if bb:
            extra.add(bb)

    rel = d["released_episode_data_array"]
    have = {x["id"] for x in rel}
    want = have | extra | {x["id"] for x in d.get("home_story_data_array", [])}
    tmpl = {x["id"]: x for x in rel}
    d["released_episode_data_array"] = [tmpl.get(i, {"id": i}) for i in sorted(want)]
    print(f"released: {len(have)} -> {len(d['released_episode_data_array'])}")

    # 2. story_event 保持 460（已经是）
    se = d["extra_story_data_list"]["story_event"]
    for it in se:
        it["state"] = 1
    print(f"story_event: {len(se)}（state 全 1）")

    new = msgpack.packb(v, use_bin_type=True)
    print(f"重编码: {len(raw)} -> {len(new)} B")

    items.pop(BASE_DECL, None)
    items[len(new)] = new
    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["load/index"] = len(new)
    m["note/index"] = 347866
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print(f"path_declared: load/index={len(new)}, note/index={m['note/index']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
