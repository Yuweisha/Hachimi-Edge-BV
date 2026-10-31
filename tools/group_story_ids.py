import struct
import msgpack
from collections import defaultdict

b = open(r"C:/Users/Schwarz/uma_replay/replay.bin", "rb").read()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
for _ in range(n):
    a, decl, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    if decl == 1224874:
        # 用我们改过的这份，但只看 9xxxxxxx 的分布
        d = msgpack.unpackb(data, raw=False, strict_map_key=False)["data"]
        nine = sorted(x["id"] for x in d["released_episode_data_array"]
                      if 90000000 <= x["id"] < 100000000)
        print(f"released 9xxxxxxx: {len(nine)}")
        groups = defaultdict(list)
        for i in nine:
            groups[str(i)[:6]].append(i)
        print("\n按前6位分组:")
        for k in sorted(groups):
            print(f"  {k}: {len(groups[k])} 个  样例 {groups[k][:4]}")
        break
