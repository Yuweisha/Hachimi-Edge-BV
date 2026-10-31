"""把 chara_list 里所有角色的 training_num / max_grade 与 1001 对齐。"""
import json
import shutil
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")

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
        if isinstance(v, dict) and "chara_list" in v.get("data", {}):
            decl0, v0 = decl, v
    except Exception:
        pass

d = v0["data"]
cl = d["chara_list"]
print(f"load/index declared={decl0}, chara_list={len(cl)} 条")

ref = next(x for x in cl if x["chara_id"] == 1001)
print("参照 1001:", {k: ref[k] for k in ("training_num", "max_grade", "love_point", "fan")})

changed = 0
for x in cl:
    if x["chara_id"] == 1001:
        continue
    if x.get("training_num") != ref["training_num"]:
        x["training_num"] = ref["training_num"]
        changed += 1
    if x.get("max_grade") != ref["max_grade"]:
        x["max_grade"] = ref["max_grade"]
print(f"改了 {changed} 条的 training_num/max_grade")

print("改后抽样:", [(x["chara_id"], x["training_num"], x["max_grade"]) for x in cl[:5]])

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_training"))
new = msgpack.packb(v0, use_bin_type=True)
print(f"重编码 {len(items[decl0])} -> {len(new)} B")

items.pop(decl0)
items[len(new)] = new
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)
print(f"replay.bin: {len(items)} 条, {len(out)} B")

m = json.loads(DECL.read_text(encoding="utf-8"))
m["load/index"] = len(new)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"path_declared load/index = {len(new)}")
