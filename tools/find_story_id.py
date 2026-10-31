import glob
import os
import struct
import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
f = max([x for x in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
         if os.path.getsize(x) == 1213518], key=os.path.getmtime)
raw = open(f, "rb").read()

# 找 90001001 的所有 msgpack 编码
targets = {
    "uint32": b"\xce" + struct.pack(">I", 90001001),
    "int64": b"\xd3" + struct.pack(">q", 90001001),
    "uint64": b"\xcf" + struct.pack(">Q", 90001001),
    "ascii": b"90001001",
}
for name, pat in targets.items():
    pos = []
    start = 0
    while True:
        i = raw.find(pat, start)
        if i < 0:
            break
        pos.append(i)
        start = i + 1
    print(f"{name}: {len(pos)} 处", pos[:6])

# 用 msgpack 结构定位：解析后找含 90001001 的字段
v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
d = v["data"]


def walk(o, path, depth=0):
    if depth > 6:
        return
    if isinstance(o, dict):
        for k, val in o.items():
            walk(val, path + [str(k)], depth + 1)
    elif isinstance(o, list):
        for i, val in enumerate(o[:2000]):
            walk(val, path + [f"[{i}]"], depth + 1)
    elif isinstance(o, int) and o == 90001001:
        print("  found:", "/".join(path))


print("\n结构定位 90001001:")
walk(d, [])
