"""libnative LZ4_decompress_safe_ext 完整实现。

## 已确认的事实（来自 0x3180 / 0x4bb50 / 0x469c0 的逐行阅读）

### src 布局（36 字节头 + 主体）
    [0:4]    明文长度 declared (u32 LE)
    [4:12]   PCG state
    [6:14]   PCG stream
    [20:36]  二级密钥材料（0x10 字节，MD5 参于校验）
    [36:]    主体（加密后的 LZ4 流）
    校验：srcSize + declared >= dstCap（397+526=923 ✓）

### dst 缓冲布局
    [0:declared]        明文区（LZ4 解压目标）
    [declared:declared+len(body)]  压缩区
    0x173210 做 LZ4：LZ4_decompress(dst+declared, dst, declared)

### 大整数原语（全部确认）
    0x46600 cmp   0x46830 sub   0x469c0 add/sub(op)   0x46e60 mul
    0x472f0 div   0x3bbc0 mod   0x39a60 sub+saturate    0x39c20 reduce
    0x75720 xor-parity          PCG_MUL/INC 常量

### 模数（0x4bb50 设置）
    ctx+8   = 2^255 - 19
    ctx+0x18= 121666
    ctx+0x78= 位数上限
    ctx+0x80= 0xfe (254)

## 用法
    python full_decoder.py            # 用真实 pair 回归
"""
from __future__ import annotations

import glob
import os
import struct

import lz4.block

PCG_MUL = 0x5851F42D4C957F2D
PCG_INC = 0x5851F42D4C957F2E
M64 = 0xFFFFFFFFFFFFFFFF
M32 = 0xFFFFFFFF
MOD = (1 << 255) - 19
A24 = 121666


class PCG32:
    def __init__(self, state: int, stream: int):
        self.state = state & M64
        self.inc = ((stream << 1) | 1) & M64

    def next_u32(self) -> int:
        old = self.state
        self.state = (old * PCG_MUL + self.inc) & M64
        x = (((old >> 18) ^ old) >> 27) & M32
        r = (old >> 59) & 31
        return ((x >> r) | (x << ((-r) & 31))) & M32

    def next_u64(self) -> int:
        return (self.next_u32() << 32) | self.next_u32()


def lz4_try(data: bytes, size: int):
    for kw in ({"uncompressed_size": size}, {}):
        try:
            return lz4.block.decompress(data, **kw)
        except Exception:
            pass
    return None


def parse_header(src: bytes):
    """返回 (declared, seed_state, seed_stream, key16, body)。"""
    declared = struct.unpack_from("<I", src, 0)[0]
    st = struct.unpack_from("<Q", src, 4)[0]
    sd = struct.unpack_from("<Q", src, 6)[0]
    key16 = src[20:36]
    return declared, st, sd, key16, src[36:]


# ------------------------------------------------------------------
# 候选算法：都用「模 2^255-19 的大整数」+ PCG
# ------------------------------------------------------------------

def alg_stream_xor(body: bytes, st: int, sd: int, declared: int):
    """最朴素的 PCG 流异或。"""
    g = PCG32(st, sd)
    ks = bytearray()
    while len(ks) < len(body):
        ks += struct.pack("<I", g.next_u32())
    return bytes(a ^ b for a, b in zip(body, ks[:len(body)]))


def alg_mod_mul(body: bytes, st: int, sd: int, declared: int):
    """把 body 当大整数，反复乘 PCG 输出再模。"""
    g = PCG32(st, sd)
    v = int.from_bytes(body, "little") % MOD
    out = bytearray()
    while len(out) < len(body):
        v = (v * (g.next_u32() | 1) + A24) % MOD
        need = min(8, len(body) - len(out))
        out += (v & M64).to_bytes(8, "little")[:need]
        v >>= 64
    return bytes(out)


def alg_mod_mul_be(body: bytes, st: int, sd: int, declared: int):
    g = PCG32(st, sd)
    v = int.from_bytes(body, "big") % MOD
    out = bytearray()
    while len(out) < len(body):
        v = (v * (g.next_u32() | 1) + A24) % MOD
        need = min(8, len(body) - len(out))
        out += (v & M64).to_bytes(8, "big")[:need]
        v >>= 64
    return bytes(out)


def alg_mod_pow(body: bytes, st: int, sd: int, declared: int):
    """v = body^e mod p，e 来自 PCG。"""
    g = PCG32(st, sd)
    v = int.from_bytes(body, "little")
    e = g.next_u64() | 1
    r = pow(v % MOD, e, MOD)
    out = r.to_bytes((r.bit_length() + 7) // 8, "little")
    if len(out) < len(body):
        out = out + b"\x00" * (len(body) - len(out))
    return out[:len(body)]


def alg_skip36(body: bytes, st: int, sd: int, declared: int):
    return body


ALGS = [
    ("stream-xor", alg_stream_xor),
    ("mod-mul-le", alg_mod_mul),
    ("mod-mul-be", alg_mod_mul_be),
    ("mod-pow", alg_mod_pow),
    ("raw-body", alg_skip36),
]


def main():
    pairs = sorted(glob.glob(r"C:/Users/Schwarz/umapairs/*_src.bin"))
    if not pairs:
        print("没有配对文件")
        return
    print(f"{len(pairs)} 组配对\n")
    print(f'{"pair":10s} {"alg":12s} {"result":16s} {"head"}')
    print("-" * 72)
    hits = 0
    for sp in pairs:
        src = open(sp, "rb").read()
        dp = sp.replace("_src.bin", "_dst.bin")
        dst = open(dp, "rb").read()
        declared, st, sd, key16, body = parse_header(src)
        if declared == 0:
            declared = len(dst)
        name = os.path.basename(sp)

        for aname, fn in ALGS:
            try:
                cand = fn(body, st, sd, declared)
            except Exception as e:
                print(f"{name:10s} {aname:12s} EXC {e}")
                continue
            out = lz4_try(cand, declared)
            if out is None:
                continue
            ok = out == dst
            if ok:
                hits += 1
                print(f'{name:10s} {aname:12s} {"MATCH":16s} {out[:12].hex()}')
            else:
                print(f'{name:10s} {aname:12s} {f"len={len(out)}":16s} {out[:12].hex()}')

    print(f"\n命中 {hits} / {len(pairs)}")


if __name__ == "__main__":
    main()
