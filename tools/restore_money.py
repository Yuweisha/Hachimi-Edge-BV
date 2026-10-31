"""在当前正常基线上恢复金币/宝石为 1 亿（保留 119 chara / 3048 event 的对齐状态）。"""
import json
import shutil
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
T = 100_000_000

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[d] = b[off:off + dl]
    off += dl

decl0 = None
v0 = None
for d, data in items.items():
    if d < 1_000_000:
        continue
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        if isinstance(v, dict) and "coin_info" in v.get("data", {}):
            decl0, v0 = d, v
    except Exception:
        pass

d = v0["data"]
print(f"load/index decl={decl0}")
print(f"  改前: coin_info={d['coin_info']}")

d["coin_info"]["fcoin"] = T
d["coin_info"]["coin"] = T

for it in d.get("item_list", []):
    if isinstance(it, dict) and it.get("item_id") == 59:
        print(f"  金币(item 59): {it.get('number')} -> {T}")
        it["number"] = T

# 顺带把时间字段保持温和值
import time
now = int(time.time())
ul = d.get("user_last_checked_time_list", [])
for x in ul:
    x["last_checked_time"] = now - 3600
hdrs = v0.get("data_headers")
if isinstance(hdrs, dict):
    hdrs["servertime"] = now

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_money_restore"))
new = msgpack.packb(v0, use_bin_type=True)
print(f"  重编码 {len(items[decl0])} -> {len(new)} B")

items.pop(decl0)
items[len(new)] = new
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)

m = json.loads(DECL.read_text(encoding="utf-8"))
m["load/index"] = len(new)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"replay.bin: {len(items)} 条, {len(out)} B")
print(f"path_declared load_index = {len(new)}")
