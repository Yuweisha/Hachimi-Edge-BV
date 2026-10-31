"""一次性全量注入 load/index：chara_list / character_story / card_list / cloth_list / released_episode。

基于当前 replay.bin 里含 coin_info 的那条，所有字段重新补齐。
可重复执行（幂等）。
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import struct
import sys

import msgpack

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"


def main() -> int:
    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items: dict[int, bytes] = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    decl0, v0 = None, None
    for decl, data in items.items():
        if decl < 1_000_000:
            continue
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
            if isinstance(v, dict) and "coin_info" in v.get("data", {}):
                decl0, v0 = decl, v
        except Exception:
            pass
    if not decl0:
        print("找不到 load/index")
        return 1

    d = v0["data"]
    print(f"load/index declared={decl0}")
    print("改前:", {k: len(d[k]) for k in
                    ("chara_list", "character_story_data_list", "card_list",
                     "cloth_list", "released_episode_data_array") if isinstance(d.get(k), list)})

    con = sqlite3.connect(MDB)
    cur = con.cursor()

    # ---- 1. chara_list：全部角色 ----
    cur.execute("SELECT id FROM chara_data ORDER BY id")
    all_chara = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT chara_id, MIN(id) FROM dress_data WHERE general_purpose=1 GROUP BY chara_id")
    dress_map = {cid: did for cid, did in cur.fetchall()}

    cl = d["chara_list"]
    have = {x["chara_id"] for x in cl}
    tpl = dict(cl[0])
    for cid in all_chara:
        if cid in have:
            continue
        e = dict(tpl)
        e.update({
            "chara_id": cid, "training_num": 0, "love_point": 1000, "fan": 1_000_000,
            "max_grade": 1, "dress_id": dress_map.get(cid, cid * 100 + 1),
            "mini_dress_id": 2, "dress_color_id": 0, "mini_dress_color_id": 0,
            "create_time": "2026-01-01 00:00:00", "love_point_pool": 0,
        })
        cl.append(e)
    cl.sort(key=lambda x: x["chara_id"])

    # ---- 2. character_story_data_list：全部角色剧情，state=1 ----
    cur.execute("SELECT id, chara_id, story_id FROM chara_story_data ORDER BY id")
    stories = cur.fetchall()
    st_tpl = dict(d["character_story_data_list"][0]) if d.get("character_story_data_list") else {}
    new_story = []
    for _rowid, cid, sid in stories:
        e = dict(st_tpl)
        e["story_id"] = sid
        e["chara_id"] = cid
        e["state"] = 1
        if "new_flag" in e:
            e["new_flag"] = 0
        new_story.append(e)
    d["character_story_data_list"] = new_story

    # ---- 3. card_list：所有 use_dress_change=1 的 dress ----
    cur.execute("SELECT id FROM dress_data WHERE use_dress_change=1 ORDER BY id")
    dress_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM card_data ORDER BY id")
    card_ids = {r[0] for r in cur.fetchall()}
    cl_tpl = dict(d["card_list"][0]) if d.get("card_list") else {}
    have_card = {x.get("card_id") for x in d.get("card_list", [])}
    for did in dress_ids:
        if did in have_card:
            continue
        e = dict(cl_tpl)
        e["card_id"] = did
        for k in ("limit_break_count", "stock", "exp"):
            if k in e:
                e[k] = 0
        d["card_list"].append(e)
    d["card_list"].sort(key=lambda x: x.get("card_id", 0))

    # ---- 4. cloth_list：全部 dress ----
    cur.execute("SELECT id FROM dress_data ORDER BY id")
    all_dress = [r[0] for r in cur.fetchall()]
    clth_tpl = dict(d["cloth_list"][0]) if d.get("cloth_list") else {}
    have_cloth = {x.get("cloth_id") for x in d.get("cloth_list", [])}
    for did in all_dress:
        if did in have_cloth:
            continue
        e = dict(clth_tpl)
        e["cloth_id"] = did
        d["cloth_list"].append(e)
    d["cloth_list"].sort(key=lambda x: x.get("cloth_id", 0))

    # ---- 5. released_episode_data_array 保持原样（已是 2121 条，元素为 dict）
    con.close()

    print("改后:", {k: len(d[k]) for k in
                    ("chara_list", "character_story_data_list", "card_list",
                     "cloth_list", "released_episode_data_array")})

    new = msgpack.packb(v0, use_bin_type=True)
    print(f"重编码 {len(items[decl0])} -> {len(new)} B")

    shutil.copy(REPLAY, REPLAY.replace(".bin", ".bin.bak_fullunlock"))
    items.pop(decl0)
    items[len(new)] = new
    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for dd, data in sorted(items.items()):
        out += struct.pack("<III", dd, dd, len(data)) + data
    open(REPLAY, "wb").write(out)
    print(f"replay.bin: {len(items)} 条, {len(out)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["load/index"] = len(new)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"path_declared load/index = {len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
