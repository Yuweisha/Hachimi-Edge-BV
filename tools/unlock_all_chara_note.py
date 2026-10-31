"""把 load/index 的 chara_list 补全到 master 全部角色，让笔记显示为已解锁。

判定：有 love_point / fan 就是解锁状态。
dress_id 从 master.dress_data 取该角色的默认服装（general_purpose=1 最小的 id）。
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

LOVE = 1000      # 亲爱度
FAN = 1_000_000  # 粉丝


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

    # 找 load/index
    decl0 = None
    v0 = None
    for decl, data in items.items():
        if decl < 1_000_000:
            continue
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
            if isinstance(v, dict) and "chara_list" in v.get("data", {}):
                decl0, v0 = decl, v
        except Exception:
            pass
    if not decl0:
        print("找不到 load/index")
        return 1

    d = v0["data"]
    cl = d["chara_list"]
    print(f"load/index declared={decl0}")
    print(f"chara_list: {len(cl)} 条")

    # master 全部角色 + 默认服装
    con = sqlite3.connect(MDB)
    cur = con.cursor()
    cur.execute("SELECT id FROM chara_data ORDER BY id")
    all_ids = [r[0] for r in cur.fetchall()]
    cur.execute("""
        SELECT chara_id, MIN(id) FROM dress_data
        WHERE general_purpose = 1
        GROUP BY chara_id
    """)
    dress = {cid: did for cid, did in cur.fetchall()}
    con.close()
    print(f"master 角色 {len(all_ids)} 个，有默认服装的 {len(dress)} 个")

    have = {x["chara_id"] for x in cl}
    missing = [i for i in all_ids if i not in have]
    print(f"缺 {len(missing)} 个，开始补")

    # 用现有条目作模板
    tpl = dict(cl[0])
    rp = d.get("rp_info", {})
    for cid in missing:
        e = dict(tpl)
        e["chara_id"] = cid
        e["training_num"] = 0
        e["love_point"] = LOVE
        e["fan"] = FAN
        e["max_grade"] = 1
        e["dress_id"] = dress.get(cid, cid * 100 + 1)
        e["mini_dress_id"] = 2
        e["dress_color_id"] = 0
        e["mini_dress_color_id"] = 0
        e["create_time"] = "2026-01-01 00:00:00"
        e["love_point_pool"] = 0
        cl.append(e)

    cl.sort(key=lambda x: x["chara_id"])
    print(f"chara_list -> {len(cl)} 条")

    shutil.copy(REPLAY, REPLAY.replace(".bin", f".bin.bak_chara_{len(cl)}"))
    new = msgpack.packb(v0, use_bin_type=True)
    print(f"重编码 {len(items[decl0])} -> {len(new)} B")

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
