"""统计 character_story_data_list 每个角色的条目数与 episode_id 分布。"""
import struct
from collections import Counter, defaultdict
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

g = defaultdict(list)
for x in cs:
    g[x["chara_id"]].append((x.get("episode_id"), x.get("story_id"), x.get("state")))

print(f"character_story_data_list: {len(cs)} 条, 覆盖 {len(g)} 个角色")
cnt = Counter(len(vv) for vv in g.values())
print(f"每角色条目数分布: {dict(sorted(cnt.items()))}")

print("\n=== 前 10 个角色 ===")
for cid in sorted(g)[:10]:
    eps = sorted(e for e, s, st in g[cid])
    print(f"  chara {cid}: {len(g[cid])} 条, episode_id={eps}")

print("\n=== 1001 (特别周) ===")
for e, s, st in sorted(g[1001]):
    print(f"  episode_id={e} story_id={s} state={st}")

print("\n=== 1002 / 1005 ===")
for cid in (1002, 1005):
    if cid in g:
        for e, s, st in sorted(g[cid]):
            print(f"  chara {cid}: episode_id={e} story_id={s} state={st}")
