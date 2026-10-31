"""看 trained_chara 的完整结构与角色对应关系。"""
import json
import struct
from collections import defaultdict
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
    if d == 1330466:
        target = data
        break

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
d = v["data"]

tc = d.get("trained_chara", [])
print(f"trained_chara: {len(tc)} 条")

# card_id -> chara_id 映射（card_id = chara_id*100 + 序号）
by_chara = defaultdict(list)
for x in tc:
    cid = x.get("card_id", 0) // 100
    by_chara[cid].append(x)

print(f"覆盖 {len(by_chara)} 个角色: {sorted(by_chara)[:15]}")

print("\n=== 一条完整记录（字段清单） ===")
one = tc[0]
print(json.dumps(one, ensure_ascii=False, indent=2)[:2500])

print("\n=== 所有字段名 ===")
print(sorted(one.keys()))
print(f"\n字段数: {len(one)}")

# 检查 1001 有几条
print(f"\nchara 1001 的育成记录: {len(by_chara.get(1001, []))} 条")
