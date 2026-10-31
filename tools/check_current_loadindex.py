"""检查当前 replay.bin 里 1330466 那份 load/index 的 character_story_data_list。"""
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

if target is None:
    print("1330466 不在库里")
    raise SystemExit(1)

v = msgpack.unpackb(target, raw=False, strict_map_key=False, unicode_errors="replace")
d = v["data"]

print("=== 关键字段 ===")
for k in ("chara_list", "character_story_data_list", "card_list", "cloth_list",
          "chara_profile_array", "released_episode_data_array"):
    val = d.get(k)
    print(f"  {k:<32} {len(val) if isinstance(val, list) else val}")

cs = d.get("character_story_data_list", [])
print(f"\ncharacter_story_data_list 首元素: {cs[0] if cs else None}")
print(f"  keys: {sorted({k for x in cs for k in x})}")

# episode_id 分布
eps = sorted(x.get("episode_id", 0) for x in cs)
print(f"  episode_id: {eps[:15]} ... {eps[-5:] if len(eps) > 5 else ''}")

# 按 chara 分组（如果有 chara_id）
if cs and "chara_id" in cs[0]:
    g = defaultdict(set)
    for x in cs:
        g[x["chara_id"]].add(x.get("episode_id"))
    cnt = Counter(len(vv) for vv in g.values())
    print(f"  每角色集数分布: {dict(cnt)}")
    print(f"  1001: {sorted(g.get(1001, []))}")
    print(f"  1002: {sorted(g.get(1002, []))}")
else:
    print("  没有 chara_id 字段（扁平结构）")

# user_last_checked_time_list
ul = d.get("user_last_checked_time_list", [])
print(f"\nuser_last_checked_time_list: {[(x.get('type'), x.get('last_checked_time')) for x in ul[:3]]}")
