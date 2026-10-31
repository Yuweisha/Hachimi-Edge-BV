"""赛马娘 API body 的 PCG 流解密器（从 libnative!LZ4_decompress_safe_ext 反汇编还原）。

数据布局：
    [u32 LE 解压后长度][16 字节 seed][数据...]
seed 从 src+4 取 16 字节：
    A = BE64(seed[0:8])
    B = BE64(seed[8:16]) * 2 + 1
    state0 = (A + B) * PCG_MULT + B
    inc    = B
密钥流每字节：rotl8(((state>>45) ^ (state>>27)) & 0xFF, state>>59)
"""
import struct

PCG_MULT = 0x5851F42D4C957F2D
MASK64 = 0xFFFFFFFFFFFFFFFF


def pcg_init_from_header(seed16: bytes):
    """从 16 字节 seed 构造 PCG 初始状态。"""
    assert len(seed16) == 16
    a = int.from_bytes(seed16[0:8], "big")
    b_raw = int.from_bytes(seed16[8:16], "big")
    inc = (b_raw * 2 + 1) & MASK64
    state = (((a + inc) & MASK64) * PCG_MULT + inc) & MASK64
    return state, inc


def pcg_next_byte(state, inc):
    """返回 (输出字节, 新状态)。

    对应 0x1070 循环体：
        rdx = old >> 45
        rax = old >> 27
        edx ^= eax                    ; 32 位
        rot = old >> 59
        al  = dl                       ; 低 8 位
        al  = al << rot                ; 8 位左移
        edx = edx >> rot               ; 32 位右移
        al |= dl
    """
    old = state
    new_state = (old * PCG_MULT + inc) & MASK64
    xorshifted = ((old >> 45) ^ (old >> 27)) & 0xFFFFFFFF
    rot = (old >> 59) & 0x1F
    lo8 = xorshifted & 0xFF
    left = (lo8 << ((-rot) & 0x1F)) & 0xFF
    right = (xorshifted >> rot) & 0xFF
    return (left | right) & 0xFF, new_state


def keystream(state, inc, n):
    out = bytearray(n)
    for i in range(n):
        out[i], state = pcg_next_byte(state, inc)
    return bytes(out), state


def decrypt(payload: bytes, header_len: int = 36, seed_off: int = 4):
    """payload = base64 解码后的完整 body。

    返回 (解压前长度, 解密后数据)。数据从 header_len 开始。
    """
    if len(payload) < header_len:
        raise ValueError("payload too short: %d" % len(payload))
    declared = struct.unpack_from("<I", payload, 0)[0]
    seed16 = payload[seed_off:seed_off + 16]
    state, inc = pcg_init_from_header(seed16)
    body = payload[header_len:]
    ks, _ = keystream(state, inc, len(body))
    plain = bytes(a ^ b for a, b in zip(body, ks))
    return declared, plain


if __name__ == "__main__":
    import base64
    import glob
    import os
    import sys

    def parse_dump(path):
        txt = open(path, "r", encoding="ascii", errors="ignore").read()
        d, cur, buf = {}, None, []
        for line in txt.splitlines():
            if line.startswith("---") and line.endswith("---"):
                if cur:
                    d[cur] = "\n".join(buf).strip()
                cur = line.strip("-")
                buf = []
            elif cur:
                buf.append(line)
            elif "=" in line:
                k, v = line.split("=", 1)
                d[k] = v
        if cur:
            d[cur] = "\n".join(buf).strip()
        return d

    for f in sorted(glob.glob("C:/FiddlerDump/*.txt")):
        d = parse_dump(f)
        b64 = d.get("RSPB64", "")
        if not b64:
            continue
        raw = base64.b64decode(b64 + "=" * ((4 - len(b64) % 4) % 4))
        if len(raw) < 40:
            continue
        print("\n=== %s ===" % os.path.basename(f))
        print("   raw=%d  declared=%d" % (len(raw), struct.unpack_from("<I", raw, 0)[0]))
        # 试不同的头长度
        for hl in (36, 20, 24, 32, 40):
            try:
                declared, plain = decrypt(raw, header_len=hl)
            except Exception as e:
                continue
            print("   header_len=%2d -> %d 字节  前24: %s" % (hl, len(plain), plain[:24].hex(" ")))
            print("                      可读: %s" % "".join(chr(c) if 32 <= c < 127 else "." for c in plain[:24]))
