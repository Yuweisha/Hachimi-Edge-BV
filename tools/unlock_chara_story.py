"""补全 character_story_data_list，消除「赛马娘剧情解锁」弹窗。

character_story_data_list 每条 {episode_id, state}，episode_id 来自
master.chara_story_data.id。补全所有条目并置 state=1。
"""
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
    shutil.copy(REPLAY, REPLAY + ".bak_cstory")

    c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
    rows = c.execute("SELECT id, chara_id FROM chara_story_data ORDER BY id").fetchall()
    print(f"master.chara_story_data: {len(rows)} 行")
    all_ids = [r[0] for r in rows]
    print("id 范围:", min(all_ids), "-", max(all_ids))

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
    cur = d.get("character_story_data_list", [])
    print(f"现有 character_story_data_list: {len(cur)} 条")

    tmpl = {x["episode_id"]: x for x in cur if isinstance(x, dict) and "episode_id" in x}
    new_arr = []
    for eid in all_ids:
        it = tmpl.get(eid, {"episode_id": eid})
        it["state"] = 1
        new_arr.append(it)
    d["character_story_data_list"] = new_arr
    print(f"新 character_story_data_list: {len(new_arr)} 条")

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
