"""查 extra_story_data_list 与 character_story_data_list 的当前状态。"""
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

if target is None:
    # 兜底：取最大的那条
    off = 8
    best = (0, None)
    for _ in range(n):
        a, d, dl = struct.unpack_from("<III", b, off)
        off += 12
        data = b[off:off + dl]
        off += dl
        if d > best[0]:
            best = (d, data)
    target = best[1]
    print("用最大条目:", best[0])

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
d = v["data"]

es = d.get("extra_story_data_list")
print("extra_story_data_list keys:", list(es.keys()) if isinstance(es, dict) else type(es))
if isinstance(es, dict):
    for k, val in es.items():
        if isinstance(val, list):
            print(f"  {k}: list[{len(val)}]")
            if val and isinstance(val[0], dict):
                print(f"     首元素 keys: {list(val[0].keys())}")
                # 统计 state
                states = {}
                for e in val:
                    s = e.get("state")
                    states[s] = states.get(s, 0) + 1
                print(f"     state 分布: {states}")
                print(f"     前 5 条: {val[:5]}")
        else:
            print(f"  {k}: {val}")

cs = d.get("character_story_data_list", [])
print(f"\ncharacter_story_data_list: {len(cs)} 条")
for cid in (1001, 1005):
    rows = [x for x in cs if x["chara_id"] == cid]
    print(f"  chara {cid}: {len(rows)} 条, states={[r.get('state') for r in rows]}")
