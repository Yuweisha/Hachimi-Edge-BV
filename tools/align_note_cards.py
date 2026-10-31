"""把 note/index 的 release_card_array 与 card_list 对齐（只保留交集）。"""
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
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[d] = b[off:off + dl]
    off += dl

cl = None
li_decl = None
for d, data in items.items():
    if d < 1_000_000:
        continue
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        if isinstance(v, dict) and "card_list" in v.get("data", {}):
            cl = {x.get("card_id") for x in v["data"]["card_list"]}
            li_decl = d
    except Exception:
        pass
print(f"card_list (decl={li_decl}): {len(cl)} 张")

note_decl = None
for d in items:
    if d in (347866, 347886, 347886):
        note_decl = d
        break
if note_decl is None:
    print("找不到 note/index（347866/347886）")
    raise SystemExit(1)

note = msgpack.unpackb(items[note_decl], raw=False, strict_map_key=False, unicode_errors="replace")
rc = set(note["data"]["release_card_array"])
print(f"note/index (decl={note_decl}) release_card_array: {len(rc)}")

merged = sorted(rc.intersection(cl))
dropped = sorted(rc.difference(cl))
print(f"对齐后: {len(merged)}（移除 {len(dropped)}）")
if dropped:
    print(f"  移除: {dropped}")

note["data"]["release_card_array"] = merged
new_note = msgpack.packb(note, use_bin_type=True)
print(f"note/index 重编码 {len(items[note_decl])} -> {len(new_note)} B")

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_step9"))
items.pop(note_decl)
items[len(new_note)] = new_note

out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd, data in sorted(items.items()):
    out += struct.pack("<III", dd, dd, len(data)) + data
REPLAY.write_bytes(out)

m = json.loads(DECL.read_text(encoding="utf-8"))
m["note/index"] = len(new_note)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"replay.bin: {len(items)} 条, {len(out)} B")
print(f"path_declared note/index = {len(new_note)}")
