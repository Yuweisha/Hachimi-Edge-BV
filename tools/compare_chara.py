"""对比 chara 1001（正常）与 1005 / 1015（异常）在 event_data_array 与 chara_list 的差异。"""
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
    if d == 1312834:
        target = data
        break

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
data = v["data"]

ev = data.get("event_data_array", [])
for cid in (1001, 1005, 1015):
    rows = [e for e in ev if e["chara_id"] == cid]
    print(f"\n=== chara {cid}: {len(rows)} 条 event ===")
    for r in rows[:8]:
        print(f"   data_id={r['data_id']} new_flag={r.get('new_flag')} create_time={r.get('create_time')}")

cl = {x["chara_id"]: x for x in data.get("chara_list", [])}
for cid in (1001, 1005, 1015):
    print(f"\n=== chara {cid} chara_list ===")
    print("  ", cl.get(cid))

cp = data.get("chara_profile_array", [])
for cid in (1001, 1005, 1015):
    rows = [x for x in cp if x["chara_id"] == cid]
    print(f"chara {cid} profile: {len(rows)} 条, data_id={[r['data_id'] for r in rows][:6]}")

cs = data.get("character_story_data_list", [])
for cid in (1001, 1005, 1015):
    rows = [x for x in cs if x["chara_id"] == cid]
    print(f"chara {cid} story: {len(rows)} 条")
