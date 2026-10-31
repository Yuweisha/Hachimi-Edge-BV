"""恢复剧情 7/7（character_story_data_list 补到 945 条）+ 确认金币宝石 1 亿。

关键：
- 结构必须是 {episode_id, state}，不加 chara_id
- episode_id = master.chara_story_data.id（1..994 中的 945 个）
- state = 1
"""
import json
import shutil
import sqlite3
import struct
import time
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
T = 100_000_000

# master 全部剧情 id
con = sqlite3.connect(MDB)
cur = con.cursor()
cur.execute("SELECT id FROM chara_story_data ORDER BY id")
all_ids = [r[0] for r in cur.fetchall()]
con.close()
print(f"master chara_story_data: {len(all_ids)} 条 (id {all_ids[0]}..{all_ids[-1]})")

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[d] = b[off:off + dl]
    off += dl

decl0, v0 = None, None
for d, data in items.items():
    if d < 1_000_000:
        continue
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        if isinstance(v, dict) and "character_story_data_list" in v.get("data", {}):
            decl0, v0 = d, v
    except Exception:
        pass

d = v0["data"]
old = d["character_story_data_list"]
print(f"\nload/index decl={decl0}")
print(f"  改前: {len(old)} 条, keys={sorted({k for x in old for k in x})}")

# 重建：只保留 {episode_id, state}
new_cs = [{"episode_id": sid, "state": 1} for sid in all_ids]
d["character_story_data_list"] = new_cs
print(f"  改后: {len(new_cs)} 条, 结构 {sorted(new_cs[0].keys())}")

# 金币/宝石
d["coin_info"]["fcoin"] = T
d["coin_info"]["coin"] = T
print(f"  coin_info: {d['coin_info']}")
for it in d.get("item_list", []):
    if isinstance(it, dict) and it.get("item_id") == 59:
        it["number"] = T
        print(f"  金币(item 59): {T}")

# 时间字段保持温和值
now = int(time.time())
for x in d.get("user_last_checked_time_list", []):
    x["last_checked_time"] = now - 3600
for k in list(d.keys()):
    if k.endswith("_last_check_time") or k.endswith("_last_checked_time"):
        if isinstance(d[k], int):
            d[k] = now - 3600
hdrs = v0.get("data_headers")
if isinstance(hdrs, dict):
    hdrs["servertime"] = now

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_final_7070"))
new = msgpack.packb(v0, use_bin_type=True)
print(f"\n重编码 {len(items[decl0])} -> {len(new)} B")

items.pop(decl0)
items[len(new)] = new
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)

m = json.loads(DECL.read_text(encoding="utf-8"))
m["load/index"] = len(new)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"replay.bin: {len(items)} 条, {len(out)} B")
print(f"path_declared load_index = {len(new)}")
