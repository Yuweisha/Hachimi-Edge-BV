"""重建 character_story_data_list：episode_id = master chara_story_data.id（全局唯一），
条目只有 {episode_id, state}，与原始结构一致。全部 state=1。
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
        if isinstance(v, dict) and "character_story_data_list" in v.get("data", {}):
            decl0, v0 = decl, v
    except Exception:
        pass

d = v0["data"]
old = d["character_story_data_list"]
print(f"load/index declared={decl0}")
print(f"改前: {len(old)} 条, keys={sorted({k for x in old for k in x})}")

# master 全部剧情 id
con = sqlite3.connect(MDB)
cur = con.cursor()
cur.execute("SELECT id FROM chara_story_data ORDER BY id")
ids = [r[0] for r in cur.fetchall()]
con.close()
print(f"master chara_story_data: {len(ids)} 条（id {ids[0]}..{ids[-1]}）")

# 保留原始已解锁的（可能有额外条目），再补全
existing = {x["episode_id"]: x.get("state", 0) for x in old}
new = []
for sid in ids:
    new.append({"episode_id": sid, "state": 1})
# 原始里有但 master 没有的，保持原样
extra = [(k, val) for k, val in existing.items() if k not in set(ids)]
for k, val in extra:
    new.append({"episode_id": k, "state": val})
new.sort(key=lambda x: x["episode_id"])

d["character_story_data_list"] = new
print(f"改后: {len(new)} 条（含 {len(extra)} 条 master 外的）")
print(f"  前 10: {new[:10]}")
print(f"  id=7  → 应该是 1001 第 7 集")
print(f"  id=8  → 应该是 1002 第 1 集")

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_csfinal"))
new_bytes = msgpack.packb(v0, use_bin_type=True)
print(f"重编码 {len(items[decl0])} -> {len(new_bytes)} B")

items.pop(decl0)
items[len(new_bytes)] = new_bytes
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)
print(f"replay.bin: {len(items)} 条, {len(out)} B")

m = json.loads(DECL.read_text(encoding="utf-8"))
m["load/index"] = len(new_bytes)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"path_declared load/index = {len(new_bytes)}")
