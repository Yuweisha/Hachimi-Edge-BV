"""查 character_story_data_list / extra_story 里是否有 new/read 标记，以及客户端「上次检查」时间字段。"""
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
d = v["data"]

print("=== character_story_data_list 字段 ===")
cs = d["character_story_data_list"]
print("  keys:", sorted(cs[0].keys()))
print("  样例:", cs[0])

print("\n=== 带 new / read / check 的顶层字段 ===")
for k, val in d.items():
    lk = k.lower()
    if any(w in lk for w in ("new", "read", "check", "last")):
        print(f"  {k} = {val if not isinstance(val, (list, dict)) else f'{type(val).__name__}({len(val)})'}")

print("\n=== user_last_checked_time_list ===")
ul = d.get("user_last_checked_time_list", [])
print(f"  {len(ul)} 条, 前 3: {ul[:3]}")

print("\n=== new_trainer_skill_last_check_time ===")
print(" ", d.get("new_trainer_skill_last_check_time"))

print("\n=== last_information_update_time ===")
print(" ", d.get("last_information_update_time"))

print("\n=== user_info 里时间相关 ===")
ui = d.get("user_info", {})
for k, val in ui.items():
    if any(w in k.lower() for w in ("time", "check", "login")):
        print(f"  {k} = {val}")
