"""改 jukebox/draw_random_request 的 music_id 为 1188。"""
import json
import shutil
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
NEW_MUSIC = 1188

m = json.loads(DECL.read_text(encoding="utf-8"))
decl = m.get("jukebox/draw_random_request")
print(f"jukebox/draw_random_request = {decl}")
key = abs(decl) if decl < 0 else decl

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[d] = b[off:off + dl]
    off += dl

data = items.get(key)
if data is None:
    print(f"库里没有 {key}")
    raise SystemExit(1)

v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
old = v["data"]["request_history"].get("music_id")
print(f"当前 music_id = {old}")

v["data"]["request_history"]["music_id"] = NEW_MUSIC
print(f"改为 {NEW_MUSIC}")

new = msgpack.packb(v, use_bin_type=True)
print(f"重编码 {len(data)} -> {len(new)} B")

if len(new) != key:
    print(f"长度变了，需要更新 path_declared: {key} -> {len(new)}")
    items.pop(key)
    items[len(new)] = new
    m["jukebox/draw_random_request"] = -len(new)
else:
    items[key] = new

shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_music"))
out = bytearray(b"RPLY") + struct.pack("<I", len(items))
for d, dd in sorted(items.items()):
    out += struct.pack("<III", d, d, len(dd)) + dd
REPLAY.write_bytes(out)
DECL.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"replay.bin: {len(items)} 条, {len(out)} B")
print(f"path_declared jukebox/draw_random_request = {m['jukebox/draw_random_request']}")
