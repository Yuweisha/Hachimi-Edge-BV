"""分析 gacha/index 和 gacha/exec 的结构，为抽卡模拟做准备。"""
import json
import sqlite3
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
MDB = r"C:/Users/Schwarz/AppData/Local/low/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    items[d] = data

print("=== 抽卡相关条目 ===")
for sz in sorted(items):
    try:
        v = msgpack.unpackb(items[sz], raw=False, strict_map_key=False, unicode_errors="replace")
        s = json.dumps(v, ensure_ascii=False)
        if "gacha" in s:
            print(f"  {sz} B  keys={list(v.keys())}")
    except Exception:
        pass

# gacha/index (2673 / 2701)
for sz in (2673, 2701):
    if sz in items:
        v = msgpack.unpackb(items[sz], raw=False, strict_map_key=False, unicode_errors="replace")
        print(f"\n=== gacha/index ({sz} B) ===")
        print(json.dumps(v, ensure_ascii=False, indent=2)[:2000])

# gacha/exec (1229)
if 1229 in items:
    v = msgpack.unpackb(items[1229], raw=False, strict_map_key=False, unicode_errors="replace")
    print(f"\n=== gacha/exec (1229 B) ===")
    print(json.dumps(v, ensure_ascii=False, indent=2)[:2500])

# master 卡池表
con = sqlite3.connect(MDB)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%gacha%'")
print("\n=== master gacha 表 ===")
for r in cur.fetchall():
    t = r[0]
    cur.execute(f"PRAGMA table_info({t})")
    cols = [c[1] for c in cur.fetchall()]
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    print(f"  {t}: {cnt} 行, 列={cols[:10]}")
con.close()
