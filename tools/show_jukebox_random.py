"""显示 jukebox/draw_random_request (344 B) 的完整明文。"""
import json
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")

m = json.loads(DECL.read_text(encoding="utf-8"))
decl = m.get("jukebox/draw_random_request")
print(f"path_declared: jukebox/draw_random_request = {decl}")

key = abs(decl) if decl < 0 else decl

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
data = None
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    if d == key:
        data = b[off:off + dl]
    off += dl

if data is None:
    print(f"库里没有 {key}")
    raise SystemExit(1)

print(f"明文 {len(data)} B")
v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")

print("\n=== 完整内容 ===")
print(json.dumps(v, ensure_ascii=False, indent=2))

out = Path(r"C:/Users/Schwarz/Downloads/jukebox_draw_random.json")
out.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已导出: {out}")
print(f"msgpack 原始文件: 也可以在会话目录找 {key} 长度的 *.msgpack")
