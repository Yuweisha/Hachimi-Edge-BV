"""给所有角色补散步记录：chara_walking_act_array 每人 12 条。

数据源：master.campaign_walking_chara 的 location_1/2/3（每角色 4-5 个 campaign，去重后 12-15 个）
目标接口：const_walking/index（path_declared 里记录 4243）
"""
import json
import shutil
import sqlite3
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"

con = sqlite3.connect(MDB)
cur = con.cursor()
cur.execute("SELECT chara_id, location_1, location_2, location_3 FROM campaign_walking_chara")
rows = cur.fetchall()
cur.execute("SELECT id FROM campaign_walking_location")
valid_loc = {r[0] for r in cur.fetchall()}
con.close()

per_chara: dict[int, list[int]] = {}
for cid, l1, l2, l3 in rows:
    s = per_chara.setdefault(cid, [])
    for v in (l1, l2, l3):
        if v and v in valid_loc and v not in s:
            s.append(v)

print(f"campaign_walking_chara: {len(rows)} 行, {len(per_chara)} 个角色")
cnt = {}
for cid, v in per_chara.items():
    cnt[len(v)] = cnt.get(len(v), 0) + 1
print(f"每角色 location 数分布: {dict(sorted(cnt.items()))}")

m = json.loads(DECL.read_text(encoding="utf-8"))
walk_decl = m.get("const_walking/index")
print(f"\nconst_walking/index declared = {walk_decl}")
if not walk_decl:
    print("path_declared 里没有 const_walking/index")
    raise SystemExit(1)

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[d] = b[off:off + dl]
    off += dl

raw = items.get(walk_decl)
if raw is None:
    print(f"库里没有 {walk_decl}")
    raise SystemExit(1)

v = msgpack.unpackb(raw, raw=False, strict_map_key=False, unicode_errors="replace")
arr = v["data"]["chara_walking_act_array"]
print(f"改前 chara_walking_act_array: {len(arr)} 条")

# 用现有条目的 create_time 做模板
tpl_time = arr[0].get("create_time", "2025-09-30 11:39:34") if arr else "2025-09-30 11:39:34"

# 已有 (chara_id, data_id) 集合
have = {(x["chara_id"], x["data_id"]) for x in arr}

added = 0
for cid, locs in sorted(per_chara.items()):
    for loc in locs:
        if (cid, loc) in have:
            continue
        arr.append({
            "chara_id": cid,
            "data_id": loc,
            "create_time": tpl_time,
            "new_flag": 0,
        })
        have.add((cid, loc))
        added += 1

arr.sort(key=lambda x: (x["chara_id"], x["data_id"]))
v["data"]["chara_walking_act_array"] = arr
print(f"补 {added} 条 -> {len(arr)} 条")
print(f"覆盖 {len({x['chara_id'] for x in arr})} 个角色")

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_walking"))
new = msgpack.packb(v, use_bin_type=True)
print(f"重编码 {len(raw)} -> {len(new)} B")

items.pop(walk_decl)
items[len(new)] = new
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)

m["const_walking/index"] = len(new)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"replay.bin: {len(items)} 条, {len(out)} B")
print(f"path_declared const_walking/index = {len(new)}")
