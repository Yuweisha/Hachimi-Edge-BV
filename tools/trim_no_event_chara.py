"""移除 chara_list 里没有事件数据的角色（图鉴遍历会卡死）。"""
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

decl0 = None
v0 = None
for d, data in items.items():
    if d < 1_000_000:
        continue
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        if isinstance(v, dict) and "chara_list" in v.get("data", {}):
            decl0, v0 = d, v
    except Exception:
        pass

dd = v0["data"]
ev_ids = {x.get("chara_id") for x in dd["event_data_array"] if x.get("chara_id")}
cl = dd["chara_list"]

kept = [x for x in cl if x.get("chara_id") in ev_ids]
removed = sorted(x.get("chara_id") for x in cl if x.get("chara_id") not in ev_ids)
print(f"chara_list: {len(cl)} -> {len(kept)}")
print(f"  移除无事件数据的角色: {removed}")

dd["chara_list"] = kept

# card_list 也要剔除这些角色（否则选角界面读到无事件角色）
cards_kept = [x for x in dd["card_list"] if (x.get("card_id") or 0) // 100 in ev_ids]
dropped_cards = sorted(x.get("card_id") for x in dd["card_list"]
                       if (x.get("card_id") or 0) // 100 not in ev_ids)
print(f"card_list: {len(dd['card_list'])} -> {len(cards_kept)}")
if dropped_cards:
    print(f"  移除卡: {dropped_cards}")
dd["card_list"] = cards_kept

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_step10"))
new = msgpack.packb(v0, use_bin_type=True)
print(f"重编码 {len(items[decl0])} -> {len(new)} B")

items.pop(decl0)
items[len(new)] = new

# note/index 的 release_card_array 也要同步
note_decl = None
for d in items:
    if d in (347816, 347866, 347886):
        note_decl = d
        break
if note_decl:
    note = msgpack.unpackb(items[note_decl], raw=False, strict_map_key=False, unicode_errors="replace")
    rc = set(note["data"]["release_card_array"])
    cl_cards = {x.get("card_id") for x in cards_kept}
    merged = sorted(rc.intersection(cl_cards))
    note["data"]["release_card_array"] = merged
    new_note = msgpack.packb(note, use_bin_type=True)
    print(f"note/index release_card_array: {len(rc)} -> {len(merged)}（{len(items[note_decl])} -> {len(new_note)} B）")
    items.pop(note_decl)
    items[len(new_note)] = new_note
    m = json.loads(DECL.read_text(encoding="utf-8"))
    m["note/index"] = len(new_note)
else:
    m = json.loads(DECL.read_text(encoding="utf-8"))

out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for dd2, data in sorted(items.items()):
    out += struct.pack("<III", dd2, dd2, len(data)) + data
REPLAY.write_bytes(out)

m["load/index"] = len(new)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"replay.bin: {len(items)} 条, {len(out)} B")
print(f"path_declared load_index = {len(new)}")
