"""用 dump 的 body + key/iv 离线验证解密，穷举可能的差异。"""
import base64, os, re, sys
from pathlib import Path

sys.path.insert(0, r"C:/Users/Schwarz/projects/Hachimi-Edge/tools")
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

D = Path(r"C:/Users/Schwarz/uma_replay/reqdump")
metas = sorted(D.glob("*.meta"), key=lambda p: p.stat().st_mtime, reverse=True)
if not metas:
    print("没有 dump")
    sys.exit(0)

meta = metas[0]
info = {}
for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        info[k.strip()] = v.strip()

body = (meta.with_suffix(".body")).read_bytes()
print(f"body {len(body)} B，path={info.get('path')}")
print(f"  key={info.get('key')}")
print(f"  iv ={info.get('iv')}")

KEY = bytes.fromhex(info["key"])
IV16 = bytes.fromhex(info["iv"])

# body 是 base64
txt = body.strip()
raw = base64.b64decode(txt + b"=" * ((4 - len(txt) % 4) % 4))
print(f"\nbase64 解码 {len(raw)} B   LE32={int.from_bytes(raw[0:4],'little')}")
print(f"  [4:36] = {raw[4:36].hex().upper()}")
cipher = raw[36:]
print(f"  密文 {len(cipher)} B")


def ks(key, iv12, ctr0, n):
    out = b""
    for i in range((n + 15) // 16):
        blk = iv12 + ((ctr0 + i) & 0xFFFFFFFF).to_bytes(4, "big")
        c = Cipher(algorithms.AES(key), modes.ECB())
        e = c.encryptor()
        out += e.update(blk) + e.finalize()
    return out[:n]


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def looks_valid(data):
    """判断解密结果像不像 LZ4 或 msgpack。"""
    if not data:
        return "空"
    # LZ4 frame magic: 04 22 4D 18
    if data[:4] == b"\x04\x22\x4D\x18":
        return "LZ4 frame"
    # msgpack map
    b0 = data[0]
    if 0x80 <= b0 <= 0x8F or b0 in (0xDE, 0xDF):
        return f"msgpack map(0x{b0:02X})"
    if b0 in (0x90, 0xDC, 0xDD):
        return f"msgpack array(0x{b0:02X})"
    return None


print("\n=== 尝试各种 IV/ctr 组合 ===")
cands = [
    ("IV16 原样 (iv12=前12, ctr=后4 BE)", IV16[:12], int.from_bytes(IV16[12:], "big")),
    ("ctr=0", IV16[:12], 0),
    ("ctr=后4 LE", IV16[:12], int.from_bytes(IV16[12:], "little")),
    ("iv12=后12, ctr=前4 BE", IV16[4:16], int.from_bytes(IV16[:4], "big")),
    ("IV12 全 0, ctr=后4", b"\x00" * 12, int.from_bytes(IV16[12:], "big")),
    ("全 0 IV", b"\x00" * 12, 0),
]

for name, iv12, ctr0 in cands:
    stream = ks(KEY, iv12, ctr0, len(cipher))
    plain = xor(cipher, stream)
    v = looks_valid(plain)
    tag = f"  ★ {v}" if v else ""
    print(f"  {name:34} 前8={plain[:8].hex().upper()}{tag}")

# 也用 key 做 ECB 直接解第一块
print("\n=== 若当成 ECB 单块 ===")
c = Cipher(algorithms.AES(KEY), modes.ECB())
d = c.decryptor()
first = d.update(cipher[:16]) + d.finalize()
print(f"  ECB 解密首块 = {first.hex().upper()}  有效={looks_valid(first)}")
