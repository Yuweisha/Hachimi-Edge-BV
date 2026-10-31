"""看 main_story_data_list 和 角色剧情相关字段的 state 分布。"""
import struct
from collections import Counter
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
d = v["data"]

ms = d.get("main_story_data_list", [])
print(f"main_story_data_list: {len(ms)} 条")
print(f"  state 分布: {Counter(x.get('state') for x in ms)}")
print(f"  前 8: {ms[:8]}")

print("\n=== 所有含 state 字段的 list ===")
for k, val in d.items():
    if isinstance(val, list) and val and isinstance(val[0], dict) and "state" in val[0]:
        print(f"  {k:<36} {len(val):>5} 条  state={dict(Counter(x.get('state') for x in val))}")

print("\n=== release_card_array (269?) ===")
rc = d.get("release_card_array", [])
print(f"  {len(rc)} 条, 前 5: {rc[:5]}")

print("\n=== story_favorite_array ===")
print(" ", d.get("story_favorite_array"))

print("\n=== short_episode_data_array ===")
se = d.get("short_episode_data_array", [])
print(f"  {len(se)} 条, 前 3: {se[:3]}")
