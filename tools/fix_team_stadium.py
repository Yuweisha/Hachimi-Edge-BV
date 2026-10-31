"""从 raw/team_stadium_index.raw 解出正确明文，替换库里错误的 453。"""
import base64
import json
import struct
from pathlib import Path

import msgpack

RAW = Path(r"C:/Users/Schwarz/uma_replay/raw/team_stadium_index.raw")
REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")

b64 = RAW.read_bytes().strip()
raw = base64.b64decode(b64 + b"=" * ((-len(b64)) % 4))
print(f"raw 文件 {len(b64)} B -> 解码 {len(raw)} B")

decl = struct.unpack_from("<I", raw, 0)[0]
print(f"[0:4] declared = {decl}")
print(f"[4:36] = {raw[4:36].hex(' ')}")

if decl == 0:
    # 不压缩：明文从 36 开始
    plain = raw[36:]
    print(f"不压缩模式，明文 {len(plain)} B")
else:
    print(f"压缩模式（declared={decl}），需要用插件解密，跳过")
    raise SystemExit(1)

v = msgpack.unpackb(plain, raw=False, strict_map_key=False, unicode_errors="replace")
print("\n=== 正确内容 ===")
print(json.dumps(v.get("data", {}), ensure_ascii=False, indent=2)[:1200])

key = len(plain)
print(f"\n明文长度 = {key}")

# 写回 replay.bin
b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
items = {}
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    items[d] = b[off:off + dl]
    off += dl

old = items.get(key)
if old == plain:
    print("库里已经是正确内容，无需替换")
else:
    if old:
        try:
            ov = msgpack.unpackb(old, raw=False, strict_map_key=False, unicode_errors="replace")
            print(f"旧内容 keys: {list(ov.get('data', {}).keys())[:5]}")
        except Exception:
            pass
    items[key] = plain
    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for d, data in sorted(items.items()):
        out += struct.pack("<III", d, d, len(data)) + data
    REPLAY.write_bytes(out)
    print(f"已替换：{len(items)} 条, {len(out)} B")
