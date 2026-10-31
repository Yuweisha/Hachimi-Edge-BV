"""看原始 character_story_data_list 的 134 条到底是什么。"""
import struct
from pathlib import Path

import msgpack

D = Path(r"C:/Users/Schwarz/uma_replay")
p = D / "replay.bin.bak_fullunlock"

b = p.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
target = None
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    if d == 1247223:
        target = data
        break

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
d = v["data"]
cs = d["character_story_data_list"]
print(f"原始 character_story_data_list: {len(cs)} 条")
print("前 10 条:")
for x in cs[:10]:
    print("  ", x)

print("\n所有出现过的 key:", sorted({k for x in cs for k in x}))

# episode_id 的分布
eps = sorted(x.get("episode_id", 0) for x in cs)
print(f"\nepisode_id 范围: {eps[0]} .. {eps[-1]}，共 {len(eps)} 个")
print(f"前 20: {eps[:20]}")

# state 分布
from collections import Counter
print(f"state 分布: {dict(Counter(x.get('state') for x in cs))}")

# 对照 master：这些 episode_id 是 chara_story_data 的 id 吗？
import sqlite3
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
con = sqlite3.connect(MDB)
cur = con.cursor()
cur.execute("SELECT id, chara_id, episode_index, story_id FROM chara_story_data ORDER BY id")
rows = cur.fetchall()
con.close()
print(f"\nmaster chara_story_data: {len(rows)} 条")
m = {r[0]: r for r in rows}
print("用 episode_id 当 master.id 查前 10 条:")
for e in eps[:10]:
    r = m.get(e)
    print(f"  episode_id={e} -> {r}")
