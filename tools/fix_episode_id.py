"""修 character_story_data_list 的 episode_id：用 master 的 episode_index。"""
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
    items = {}
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
            if isinstance(v, dict) and "character_story_data_list" in v.get("data", {}):
                decl0, v0 = decl, v
        except Exception:
            pass
    if not decl0:
        print("找不到 load/index")
        return 1

    d = v0["data"]
    cs = d["character_story_data_list"]
    print(f"load/index declared={decl0}")
    print(f"character_story_data_list: {len(cs)} 条")
    print("改前 1001:", [(x['episode_id'], x['story_id']) for x in cs if x['chara_id'] == 1001])

    # master: story_id -> episode_index
    con = sqlite3.connect(MDB)
    cur = con.cursor()
    cur.execute("SELECT story_id, episode_index FROM chara_story_data")
    ep_map = {sid: ep for sid, ep in cur.fetchall()}
    con.close()
    print(f"master 映射: {len(ep_map)} 条")

    fixed = 0
    for x in cs:
        sid = x.get("story_id")
        ep = ep_map.get(sid)
        if ep is not None and x.get("episode_id") != ep:
            x["episode_id"] = ep
            fixed += 1
    print(f"修正 {fixed} 条的 episode_id")
    print("改后 1001:", [(x['episode_id'], x['story_id']) for x in cs if x['chara_id'] == 1001])

    shutil.copy(REPLAY, REPLAY.replace(".bin", ".bin.bak_epfix"))
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
