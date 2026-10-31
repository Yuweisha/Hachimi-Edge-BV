"""把会话目录里缺的 msgpack（按长度）补进 replay.bin。"""
import glob
import os
import shutil
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
GD = Path(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn")

# 需要补的明文长度（不压缩接口 + 变化了的接口）
WANT = {164, 220, 342, 6094, 62484}

sess = sorted(glob.glob(str(GD / "hachimi" / "http" / "*")), key=os.path.getmtime)[-1]
print("会话:", os.path.basename(sess))

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, decl, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[decl] = b[off:off + dl]
    off += dl
print(f"旧 replay.bin: {len(items)} 条")
print(f"  已有: {sorted(x for x in WANT if x in items)}")
print(f"  缺:   {sorted(x for x in WANT if x not in items)}")

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_add"))

added = []
for f in sorted(glob.glob(os.path.join(sess, "*.msgpack"))):
    sz = os.path.getsize(f)
    if sz not in WANT or sz in items:
        continue
    data = Path(f).read_bytes()
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
    except Exception as e:
        print(f"  跳过 {os.path.basename(f)}: {e}")
        continue
    keys = list(v.keys())[:3] if isinstance(v, dict) else "?"
    print(f"  + {sz:>6} B  {os.path.basename(f)}  keys={keys}")
    items[sz] = data
    added.append(sz)

out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for d, data in sorted(items.items()):
    out += struct.pack("<III", d, d, len(data)) + data
REPLAY.write_bytes(out)
print(f"\nreplay.bin: {len(items)} 条, {len(out)} B（新增 {len(added)} 条: {added}）")
