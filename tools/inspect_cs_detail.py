"""查 character_story_data_list 里 1001/1005 的完整条目（episode_id 对不对）。"""
import struct
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
    if d == 1330466:
        target = data
        break

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
cs = v["data"]["character_story_data_list"]

for cid in (1001, 1002, 1005):
    rows = [x for x in cs if x["chara_id"] == cid]
    print(f"\n=== chara {cid}: {len(rows)} 条 ===")
    for r in sorted(rows, key=lambda x: x.get("episode_id", 0)):
        print("  ", r)

# master 里 1001 的剧情 id
import sqlite3
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
con = sqlite3.connect(MDB)
cur = con.cursor()
cur.execute("SELECT id, chara_id, episode_index, story_id FROM chara_story_data WHERE chara_id=1001 ORDER BY id")
print("\n=== master chara_story_data (chara 1001) ===")
for r in cur.fetchall():
    print("  id=%s chara=%s episode_index=%s story_id=%s" % r)
con.close()
