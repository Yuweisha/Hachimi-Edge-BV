"""Tempest/LZ4_decompress_safe_ext 的完整实现尝试（基于已确认的事实）。

已由反编译确认的部分：
  1. ctx+8   = 模数 2^255-19 ; ctx+0x18 = 121666 ; ctx+0x78 = 位数上限 ; ctx+0x80 = 0xfe
  2. PCG 种子：state = src[0:8], stream = src[2:10]（0x33180 的初始化原样）
  3. 常量 PCG_MUL/PCG_INC，以及大量 8 字节倒序（大端转换）片段
  4. 输出层 0x173210 是标准 LZ4 block 解压
  5. src[0:4] = 解压后明文长度（12/12 样本自洽）

未确认的：中间的大整数变换的具体顺序。本文件把各种「合理顺序」都实现成
独立函数，用真实 pair 逐字节验证，命中的那个就是正确答案。

用法: python tempest_impl.py
"""
from __future__ import annotations

import glob
import os
import struct

import lz4.block

PCG_MUL = 0x5851F42D4C957F2D
PCG_INC = 0x5851F42D4C957F2E
MASK64 = 0xFFFFFFFFFFFFFFFF
MASK32 = 0xFFFFFFFF
P25519 = (1 << 255) - 19


class PCG32:
    def __init__(self, state: int, stream: int):
        self.state = state & MASK64
        self.inc = ((stream << 1) | 1) & MASK64

    @classmethod
    def from_payload(cls, buf: bytes, off: int = 0):
        return cls(struct.unpack_from("<Q", buf, off)[0],
                   struct.unpack_from("<Q", buf, off + 2)[0])

    def next_u32(self) -> int:
        old = self.state
        self.state = (old * PCG_MUL + self.inc) & MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & MASK32
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & MASK32

    def bytes_le(self, n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            out += struct.pack("<I", self.next_u32())
        return bytes(out[:n])


def bswap8(b: bytes) -> bytes:
    """8 字节倒序（反编译里反复出现的 >>0x38 | ... <<0x38 模式）。"""
    out = bytearray(len(b))
    for i in range(0, len(b) - 7, 8):
        out[i:i + 8] = b[i:i + 8][::-1]
    return bytes(out)


def try_lz4(data: bytes, n: int):
    for kw in ({"uncompressed_size": n}, {}):
        try:
            return lz4.block.decompress(data, **kw)
        except Exception:
            pass
    return None


# ------------------------------------------------------------------
# 候选变换：(名字, 函数(payload, declared) -> 候选 LZ4 流)
# ------------------------------------------------------------------

def v_raw(payload, n):
    return payload


def v_skip10(payload, n):
    return payload[10:]


def v_pcg_xor(payload, n):
    g = PCG32.from_payload(payload)
    ks = g.bytes_le(len(payload) - 10)
    return bytes(a ^ b for a, b in zip(payload[10:], ks))


def v_pcg_xor_bswap(payload, n):
    g = PCG32.from_payload(payload)
    ks = bswap8(g.bytes_le(len(payload) - 10))
    return bytes(a ^ b for a, b in zip(payload[10:], ks))


def v_mod_pcg(payload, n):
    """把 payload 当大整数（大端），反复乘 PCG 输出再取模。"""
    g = PCG32.from_payload(payload)
    v = int.from_bytes(payload[10:], "big") % P25519
    out = bytearray()
    while len(out) < len(payload) - 10:
        v = (v * g.next_u32() + 121666) % P25519
        need = min(8, len(payload) - 10 - len(out))
        out += v.to_bytes(8, "big")[:need]
    return bytes(out)


def v_mod_pcg_le(payload, n):
    g = PCG32.from_payload(payload)
    v = int.from_bytes(payload[10:], "little") % P25519
    out = bytearray()
    while len(out) < len(payload) - 10:
        v = (v * g.next_u32() + 121666) % P25519
        need = min(8, len(payload) - 10 - len(out))
        out += v.to_bytes(8, "little")[:need]
    return bytes(out)


def v_bswap_then_xor(payload, n):
    body = bswap8(payload[10:])
    g = PCG32.from_payload(payload)
    ks = g.bytes_le(len(body))
    return bytes(a ^ b for a, b in zip(body, ks))


VARIANTS = [
    ("raw", v_raw),
    ("skip10", v_skip10),
    ("pcg-xor", v_pcg_xor),
    ("pcg-xor+bs", v_pcg_xor_bswap),
    ("mod-pcg-be", v_mod_pcg),
    ("mod-pcg-le", v_mod_pcg_le),
    ("bswap+xor", v_bswap_then_xor),
]


def main():
    pairs = sorted(glob.glob(r"C:/Users/Schwarz/umapairs/*_src.bin"))
    print(f"{len(pairs)} 个真实配对\n")
    if not pairs:
        print("没有配对文件")
        return

    print(f'{"pair":10s} {"variant":14s} {"lz4":6s} {"len":>10s} {"match":6s}')
    print("-" * 60)
    hits = 0
    for sp in pairs:
        src = open(sp, "rb").read()
        dp = sp.replace("_src.bin", "_dst.bin")
        if not os.path.exists(dp):
            continue
        dst = open(dp, "rb").read()
        declared = struct.unpack_from("<I", src, 0)[0]
        payload = src[4:]

        for name, fn in VARIANTS:
            try:
                cand = fn(payload, declared)
            except Exception:
                continue
            out = try_lz4(cand, declared)
            if out is None:
                continue
            ok = out == dst
            if ok:
                hits += 1
            print(f'{os.path.basename(sp):10s} {name:14s} {"OK":6s} {len(out):>10,} '
                  f'{"MATCH" if ok else "no":6s}  {out[:16].hex()}')

    print(f"\n命中 {hits} 组")


if __name__ == "__main__":
    main()
