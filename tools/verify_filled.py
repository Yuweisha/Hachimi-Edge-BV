"""验证新填入的明文是否与目标接口语义匹配（抽查关键几个）。"""
import json
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

cur = json.loads(DECL.read_text(encoding="utf-8"))

CHECK = [
    "gacha/exec", "gacha/get_history", "schedule_book/index",
    "support_card_deck/index", "friend/search", "jobs/start",
    "circle/room_enter", "trainer_skill/index",
    "user/change_favorite_character", "jukebox/index",
    "jukebox/draw_random_request", "mission/receive",
]

for api in CHECK:
    key = cur.get(api)
    if key is None:
        print(f"{api}: 表里没有")
        continue
    sz = abs(key) if key < 0 else key
    data = items.get(sz)
    if not data:
        print(f"{api}: 库里没有 {sz}")
        continue
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
    except Exception as e:
        print(f"{api}: 解不开 {e}")
        continue
    d = v.get("data")
    keys = list(d.keys())[:6] if isinstance(d, dict) else None
    print(f"{api:<34} {sz:>7}  data keys={keys}")
