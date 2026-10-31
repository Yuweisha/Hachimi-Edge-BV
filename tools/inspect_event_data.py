"""查 event_data_array 结构和覆盖情况。"""
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

ev = d.get("event_data_array", [])
print(f"event_data_array: {len(ev)} 条")

# 按 chara_id 分组
from collections import defaultdict
g = defaultdict(list)
for e in ev:
    g[e["chara_id"]].append(e["data_id"])

print(f"覆盖 {len(g)} 个角色")
for cid in sorted(g)[:5]:
    print(f"  chara {cid}: {len(g[cid])} 条 data_id，前几个 {sorted(g[cid])[:6]}")

# 1001 vs 1005
for cid in (1001, 1002, 1005, 1015):
    print(f"  chara {cid}: {len(g.get(cid, []))} 条")

# chara_list 里哪些没有 event
cl = {x["chara_id"] for x in d.get("chara_list", [])}
missing = sorted(cl - set(g.keys()))
print(f"\nchara_list 有但 event_data 没有的: {len(missing)} 个")
print(" ", missing[:20])
