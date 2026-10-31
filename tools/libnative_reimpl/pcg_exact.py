"""PCG 初始化精确还原（0x3180 的 local_240 / local_248）。

反编译原文：
    local_240 = CONCAT71(local_3d8[2], local_3d8[9], local_3d8[10], local_3d8[11],
                         local_3d8[3], local_3d8[13], local_3d8[14], local_3d8[15]) * 2 | 1;
    local_248 = CONCAT71(local_3d8[0], local_3d8[1], local_3d8[2], local_3d8[3],
                         local_3d8[1], local_3d8[5], local_3d8[6], local_3d8[7]) * PCG_MUL
              + local_240 * PCG_INC;

Ghidra 的 CONCAT71 是「高位在左、低位在右」，所以内存里的实际字节序需要反过来：
    CONCAT71(a,b,c,d,e,f,g,h) 的 8 字节 = h g f e d c b a（小端）

由此：
    inc_bytes   = local_3d8[15], [14], [13], [3], [11], [10], [9], [2]   → 反转后
    state_bytes = local_3d8[7], [6], [5], [1], [3], [2], [1], [0]        → 反转后

其中 local_3d8 = src + 4。
"""
from __future__ import annotations

import struct

PCG_MUL = 0x5851F42D4C957F2D
PCG_INC = 0x5851F42D4C957F2E
M64 = 0xFFFFFFFFFFFFFFFF
M32 = 0xFFFFFFFF


def ghidra_concat71(*bytes_hi_to_lo: int) -> int:
    """CONCAT71(h7,h6,h5,h4,h3,h2,h1,h0) -> 小端整数。

    Ghidra 的 CONCAT 把第一个参数放最高字节。所以：
        value = h7<<56 | h6<<48 | ... | h0
    """
    v = 0
    for b in bytes_hi_to_lo:
        v = (v << 8) | (b & 0xFF)
    return v


def seeds_from_payload(payload: bytes, off: int = 0):
    """payload = src[4:]，off 用于指向 local_3d8 在该 buffer 中的起点。"""
    b = payload

    def at(i):
        return b[off + i]

    # local_240（inc 的种子）：参数顺序 [2], [9], [10], [11], [3], [13], [14], [15]
    inc_seed = ghidra_concat71(at(2), at(9), at(10), at(11), at(3), at(13), at(14), at(15))
    # local_248（state 的种子）：[0], [1], [2], [3], [1], [5], [6], [7]
    st_seed = ghidra_concat71(at(0), at(1), at(2), at(3), at(1), at(5), at(6), at(7))
    return inc_seed, st_seed


class PCG32Exact:
    """精确匹配 0x3180 的 PCG 初始化。"""

    def __init__(self, payload: bytes, off: int = 0):
        inc_seed, st_seed = seeds_from_payload(payload, off)
        self.inc = ((inc_seed << 1) | 1) & M64
        # state 已经推进过一次
        self.state = (st_seed * PCG_MUL + self.inc * PCG_INC) & M64

    def next_u32(self) -> int:
        old = self.state
        self.state = (old * PCG_MUL + self.inc) & M64
        x = (((old >> 18) ^ old) >> 27) & M32
        r = (old >> 59) & 31
        return ((x >> r) | (x << ((-r) & 31))) & M32

    def ks(self, n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            out += struct.pack("<I", self.next_u32())
        return bytes(out[:n])


if __name__ == "__main__":
    import glob
    import os

    import lz4.block

    print(f'{"pair":10s} {"variant":20s} {"result":14s} {"head"}')
    print("-" * 70)
    hits = 0
    for sp in sorted(glob.glob(r"C:/Users/Schwarz/umapairs/*_src.bin")):
        src = open(sp, "rb").read()
        dp = sp.replace("_src.bin", "_dst.bin")
        dst = open(dp, "rb").read()
        declared = struct.unpack_from("<I", src, 0)[0] or len(dst)
        payload = src[4:]
        name = os.path.basename(sp)

        g = PCG32Exact(payload, 0)
        ks = g.ks(len(payload))

        variants = {
            "xor@0": bytes(a ^ b for a, b in zip(payload, ks)),
            "xor@32": bytes(a ^ b for a, b in zip(payload[32:], ks)),
            "xor@36": bytes(a ^ b for a, b in zip(payload[36:], ks)),
        }
        for vname, cand in variants.items():
            for kw in ({"uncompressed_size": declared}, {}):
                try:
                    out = lz4.block.decompress(cand, **kw)
                    ok = out == dst
                    if ok:
                        hits += 1
                    print(f'{name:10s} {vname:20s} {"MATCH" if ok else f"len={len(out)}":14s} {out[:12].hex()}')
                    break
                except Exception:
                    pass
    print(f"\n命中 {hits}")
