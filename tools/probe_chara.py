import glob
import os
import sqlite3
import struct
import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"

# 从 replay.bin 取当前 load/index
b = open(r"C:/Users/Schwarz/uma_replay/replay.bin", "rb").read()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
d = None
best = 0
for _ in range(n):
    a, decl, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False)
        dd = v.get("data") if isinstance(v, dict) else None
        if isinstance(dd, dict) and "coin_info" in dd:
            d = dd
            best = decl
    except Exception:
        pass
print("用 load/index declared =", best)

for k in ("chara_list", "card_list", "cloth_list", "chara_profile_array"):
    arr = d.get(k, [])
    print(f"\n{k}: {len(arr)} 条")
    if arr and isinstance(arr[0], dict):
        print("  键:", list(arr[0].keys()))
        print("  样例:", arr[:2])

# master 侧总数
c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
for t in ("chara_data", "chara_card_data", "dress_data"):
    try:
        cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        cols = [x[1] for x in c.execute(f"PRAGMA table_info({t})")]
        print(f"\nmaster.{t}: {cnt} 行, 列: {cols[:8]}")
    except Exception as e:
        print(f"\nmaster.{t}: {e}")
