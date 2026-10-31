import struct
import msgpack

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"

b = open(REPLAY, "rb").read()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
entries = []
for _ in range(n):
    a, decl, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    entries.append((decl, data))

pats = {
    "u32": b"\xce" + struct.pack(">I", 90001001),
    "i64": b"\xd3" + struct.pack(">q", 90001001),
    "u64": b"\xcf" + struct.pack(">Q", 90001001),
}
# 也搜 90001003（已知在 released 里）做对照
pats2 = {
    "u32_003": b"\xce" + struct.pack(">I", 90001003),
    "i64_003": b"\xd3" + struct.pack(">q", 90001003),
}

for decl, data in sorted(entries, key=lambda x: -x[0])[:12]:
    hits = {k: data.count(p) for k, p in pats.items() if data.count(p)}
    hits2 = {k: data.count(p) for k, p in pats2.items() if data.count(p)}
    if hits or hits2:
        print(f"declared={decl}: 001->{hits}  003->{hits2}")

# 结构定位：在 read_info 里找含 90001003 的路径
for decl, data in entries:
    if decl == 60361:
        d = msgpack.unpackb(data, raw=False, strict_map_key=False)["data"]
        for k, arr in d.items():
            if isinstance(arr, list):
                ids = [x.get("id") for x in arr if isinstance(x, dict)]
                nine = [i for i in ids if i and 90000000 <= i < 100000000]
                if nine:
                    print(f"\nread_info.{k}: {len(arr)} 条, 9xxxxxxx={len(nine)}, 样例={nine[:6]}")
        break
