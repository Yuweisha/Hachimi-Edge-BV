"""查 read_info/index（71717）的结构和 state。"""
import struct
from collections import Counter
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
    if d == 71717:
        target = data
        break

if target is None:
    print("read_info/index (71717) 不在库里")
    raise SystemExit(0)

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
print("read_info/index 顶层 keys:", list(v.keys()))
d = v.get("data", {})
print("data keys:", list(d.keys()))
for k, val in d.items():
    if isinstance(val, list):
        print(f"  {k}: list[{len(val)}]")
        if val and isinstance(val[0], dict):
            print(f"     首元素: {val[0]}")
            if "state" in val[0]:
                print(f"     state 分布: {Counter(x.get('state') for x in val)}")
    elif isinstance(val, dict):
        print(f"  {k}: dict keys={list(val.keys())[:10]}")
    else:
        print(f"  {k}: {val}")
