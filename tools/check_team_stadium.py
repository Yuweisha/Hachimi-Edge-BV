"""检查 team_stadium/index (453 B) 的数据结构。"""
import json
import sqlite3
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
    if d == 453:
        target = data
        break

if target is None:
    print("453 不在库里")
    raise SystemExit(1)

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
print("=== team_stadium/index 完整内容 ===")
print(json.dumps(v, ensure_ascii=False, indent=2))

# 对照 load/index 里的 team_stadium 相关字段
print("\n=== load/index 里的 team_stadium 字段 ===")
b2 = Path(r"C:/Users/Schwarz/uma_replay/replay.bin").read_bytes()
n2 = struct.unpack_from("<I", b2, 4)[0]
off2 = 8
li = None
for _ in range(n2):
    a, d, dl = struct.unpack_from("<III", b2, off2)
    off2 += 12
    data = b2[off2:off2 + dl]
    off2 += dl
    if d == 1307450:
        li = data
        break
if li:
    lv = msgpack.unpackb(li, raw=False, strict_map_key=False, unicode_errors="replace")
    ld = lv["data"]
    for k in ("team_stadium_race_status", "team_stadium_user", "team_data_array"):
        print(f"  {k} = {json.dumps(ld.get(k), ensure_ascii=False)[:300]}")
