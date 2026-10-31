import struct
import msgpack
from collections import Counter

b = open(r"C:/Users/Schwarz/uma_replay/replay.bin", "rb").read()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
for _ in range(n):
    a, decl, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    if decl == 1224874:
        d = msgpack.unpackb(data, raw=False, strict_map_key=False)["data"]
        ev = d.get("event_data_array", [])
        ids = [x.get("data_id") for x in ev if isinstance(x, dict)]
        print("event_data_array:", len(ev))
        nine = [i for i in ids if i and 90000000 <= i < 100000000]
        print("9xxxxxxx 条目:", len(nine), "样例:", nine[:8])

        def pre(i):
            s = str(i)
            return s[:2] if len(s) > 2 else s

        print("前缀分布:", Counter(pre(i) for i in ids if i).most_common(8))

        rel9 = {x["id"] for x in d["released_episode_data_array"] if 90000000 <= x["id"] < 100000000}
        print()
        print("released 9xxxxxxx:", len(rel9))
        print("event_data 9xxxxxxx 去重:", len(set(nine)))
        print("交集:", len(rel9.intersection(set(nine))))
