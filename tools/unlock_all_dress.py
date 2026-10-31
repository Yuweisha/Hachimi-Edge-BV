"""补全 card_list 到所有 use_dress_change=1 的 dress，解锁全部换装。"""
import json
import shutil
import sqlite3
import struct
import sys

import msgpack

M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_dress")

    c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
    dresses = [(r[0], r[1]) for r in
               c.execute("SELECT id, general_purpose FROM dress_data WHERE use_dress_change=1 ORDER BY id")]
    print(f"use_dress_change=1: {len(dresses)} 个")

    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    target_decl = 0
    target_data = None
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        data = b[off:off + dl]
        off += dl
        items[decl] = data
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False)
            dd = v.get("data") if isinstance(v, dict) else None
            if isinstance(dd, dict) and "coin_info" in dd and decl > target_decl:
                target_decl, target_data = decl, data
        except Exception:
            pass
    print(f"load/index declared={target_decl}")

    v = msgpack.unpackb(target_data, raw=False, strict_map_key=False)
    d = v["data"]

    cur = d.get("card_list", [])
    have = {x["card_id"] for x in cur}
    tmpl = cur[0]
    added = 0
    for dress_id, general in dresses:
        if dress_id in have:
            continue
        it = dict(tmpl)
        it.update({
            "card_id": dress_id,
            "rarity": 3,
            "talent_level": 1,
            "create_time": "2024-01-01 00:00:00",
            "skill_data_array": [],
        })
        cur.append(it)
        added += 1
    d["card_list"] = cur
    print(f"card_list: +{added} -> {len(cur)}")

    new = msgpack.packb(v, use_bin_type=True)
    print(f"重编码: {len(target_data)} -> {len(new)} B")

    items.pop(target_decl, None)
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
