"""查 note/get_new_chara_data 和 note/get_directory_card 的明文。"""
import struct
from pathlib import Path

import msgpack

b = Path(r"C:/Users/Schwarz/uma_replay/replay.bin").read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
targets = {}
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    if d in (3538, 103254):
        targets[d] = data

for sz in (3538, 103254):
    data = targets.get(sz)
    if not data:
        print(f"\n=== {sz} 不在库里 ===")
        continue
    v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
    print(f"\n=== {sz} B ===")
    print("顶层 keys:", list(v.keys()))
    d = v.get("data", {})
    print("data keys:", list(d.keys()) if isinstance(d, dict) else type(d))
    if isinstance(d, dict):
        for k, val in d.items():
            if isinstance(val, list):
                print(f"  {k}: list[{len(val)}]")
                if val and isinstance(val[0], dict):
                    print(f"     首元素: {val[0]}")
            elif isinstance(val, dict):
                print(f"  {k}: dict, keys={list(val.keys())[:8]}")
            else:
                print(f"  {k}: {val}")
