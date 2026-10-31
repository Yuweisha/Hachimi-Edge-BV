"""消掉「新解锁」弹窗和 NEW 标签：
1. user_last_checked_time_list 的时间戳推到未来
2. event_data_array / chara_profile_array 的 new_flag 清零
3. 各类 *_last_check_time 推到未来
"""
import json
import shutil
import struct
import time
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")

# 未来时间戳（当前 + 30 天）
FUTURE = int(time.time()) + 30 * 86400
print(f"目标时间戳: {FUTURE}")

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, decl, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[decl] = b[off:off + dl]
    off += dl

decl0, v0 = None, None
for decl, data in items.items():
    if decl < 1_000_000:
        continue
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        if isinstance(v, dict) and "user_last_checked_time_list" in v.get("data", {}):
            decl0, v0 = decl, v
    except Exception:
        pass

d = v0["data"]
print(f"load/index declared={decl0}")

# 1) user_last_checked_time_list
ul = d.get("user_last_checked_time_list", [])
print(f"\nuser_last_checked_time_list: {len(ul)} 条")
for x in ul:
    old = x.get("last_checked_time")
    x["last_checked_time"] = FUTURE
    print(f"  type={x.get('type')}: {old} -> {FUTURE}")

# 2) new_flag 清零
cleared = 0
for key in ("event_data_array", "chara_profile_array", "card_list", "cloth_list", "chara_list"):
    arr = d.get(key)
    if not isinstance(arr, list):
        continue
    c = 0
    for x in arr:
        if isinstance(x, dict) and "new_flag" in x and x["new_flag"] != 0:
            x["new_flag"] = 0
            c += 1
    if c:
        print(f"  {key}: 清掉 {c} 个 new_flag")
    cleared += c

# 3) 各类 last_check_time
for k in list(d.keys()):
    if k.endswith("_last_check_time") or k.endswith("_last_checked_time"):
        old = d[k]
        if isinstance(old, int):
            d[k] = FUTURE
            print(f"  {k}: {old} -> {FUTURE}")

# 4) last_information_update_time 也推到未来
if "last_information_update_time" in d:
    print(f"  last_information_update_time: {d['last_information_update_time']} (保持)")

print(f"\n共清 {cleared} 个 new_flag")

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_nonew"))
new_bytes = msgpack.packb(v0, use_bin_type=True)
print(f"重编码 {len(items[decl0])} -> {len(new_bytes)} B")

items.pop(decl0)
items[len(new_bytes)] = new_bytes
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)
print(f"replay.bin: {len(items)} 条, {len(out)} B")

m = json.loads(DECL.read_text(encoding="utf-8"))
m["load/index"] = len(new_bytes)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"path_declared load/index = {len(new_bytes)}")
