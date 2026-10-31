"""重建 card_list：只保留 master.card_data 里存在的 card_id。

之前误用 dress_data.id 填充，导致 128 个无效卡 ID → 「强化编成」软死。
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

b = REPLAY.read_bytes()
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
        if isinstance(v, dict) and "card_list" in v.get("data", {}):
            decl0, v0 = decl, v
    except Exception:
        pass

d = v0["data"]
cl = d["card_list"]
print(f"load/index declared={decl0}")
print(f"card_list: {len(cl)} 条")

con = sqlite3.connect(MDB)
cur = con.cursor()
cur.execute("SELECT id, chara_id FROM card_data")
rows = cur.fetchall()
con.close()
valid = {r[0]: r[1] for r in rows}
print(f"master card_data: {len(valid)} 张")

# 保留合法的
good = [x for x in cl if x.get("card_id") in valid]
bad = [x.get("card_id") for x in cl if x.get("card_id") not in valid]
print(f"合法 {len(good)} 条，剔除 {len(bad)} 条")
if bad:
    print(f"  剔除样本: {bad[:10]}")

# 补充：master 里所有卡都加上（如果缺失）
have = {x.get("card_id") for x in good}
tpl = dict(good[0]) if good else {}
added = 0
for cid, chara_id in rows:
    if cid in have:
        continue
    e = dict(tpl)
    e["card_id"] = cid
    for k in ("limit_break_count", "stock", "exp"):
        if k in e:
            e[k] = 0
    good.append(e)
    added += 1
print(f"补全 {added} 张（master 有但列表里没有的）")

good.sort(key=lambda x: x.get("card_id", 0))
d["card_list"] = good
print(f"card_list -> {len(good)} 条")

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_cardfix"))
new = msgpack.packb(v0, use_bin_type=True)
print(f"重编码 {len(items[decl0])} -> {len(new)} B")

items.pop(decl0)
items[len(new)] = new
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)
print(f"replay.bin: {len(items)} 条, {len(out)} B")

m = json.loads(DECL.read_text(encoding="utf-8"))
m["load/index"] = len(new)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"path_declared load/index = {len(new)}")
