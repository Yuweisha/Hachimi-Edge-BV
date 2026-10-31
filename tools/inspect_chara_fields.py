"""查 load/index 里所有与角色绑定的 list 字段。"""
import struct
from pathlib import Path

import msgpack

b = Path(r"C:/Users/Schwarz/uma_replay/replay.bin").read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
target = None
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    if d == 1312834:
        target = data
        break

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
d = v["data"]

cp = d.get("chara_profile_array", [])
cp_ids = {x["chara_id"] for x in cp}
print(f"chara_profile_array: {len(cp)} 条, {len(cp_ids)} 个不同 chara_id")
print("  1001-1015 里缺:", [c for c in range(1001, 1016) if c not in cp_ids])

print("\n=== 含 chara_id / dress_id / card_id 的 list 字段 ===")
for k, val in d.items():
    if not isinstance(val, list) or not val or not isinstance(val[0], dict):
        continue
    keys = set(val[0].keys())
    if keys.intersection({"chara_id", "dress_id", "card_id"}):
        ids = set()
        for x in val:
            vv = x.get("chara_id") or x.get("dress_id") or x.get("card_id")
            if vv:
                ids.add(vv)
        print(f"  {k:<42} {len(val):>5} 条 / {len(ids):>4} 个 id")
        print(f"      keys = {sorted(keys)[:8]}")

print("\n=== main_story_data_list[0] ===")
ms = d.get("main_story_data_list", [])
if ms:
    print(" ", ms[0])
print("\n=== character_story_data_list[0] ===")
cs = d.get("character_story_data_list", [])
if cs:
    print(" ", cs[0])
