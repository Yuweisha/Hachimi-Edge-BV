import glob
import os
import struct

import lz4.block

PCG_MUL = 0x5851F42D4C957F2D
PCG_INC = 0x5851F42D4C957F2E
M64 = 0xFFFFFFFFFFFFFFFF
M32 = 0xFFFFFFFF


class PCG:
    def __init__(self, s, st):
        self.s = s & M64
        self.inc = ((st << 1) | 1) & M64

    def u32(self):
        old = self.s
        self.s = (old * PCG_MUL + self.inc) & M64
        x = (((old >> 18) ^ old) >> 27) & M32
        r = (old >> 59) & 31
        return ((x >> r) | (x << ((-r) & 31))) & M32

    def ks(self, n):
        out = bytearray()
        while len(out) < n:
            out += struct.pack("<I", self.u32())
        return bytes(out[:n])


def main():
    for sp in sorted(glob.glob(r"C:/Users/Schwarz/umapairs/*_src.bin")):
        src = open(sp, "rb").read()
        dp = sp.replace("_src.bin", "_dst.bin")
        dst = open(dp, "rb").read() if os.path.exists(dp) else b""
        declared = struct.unpack_from("<I", src, 0)[0] or len(dst)
        name = os.path.basename(sp)
        print(f"\n{name} src={len(src)} dst={len(dst)} declared={declared}")

        for body_off in (36, 20, 32, 4):
            body = src[body_off:]
            if len(body) < 8:
                continue
            for seed_off in (4, 6, 8, 0):
                if seed_off + 10 > len(src):
                    continue
                s1 = struct.unpack_from("<Q", src, seed_off)[0]
                s2 = struct.unpack_from("<Q", src, seed_off + 2)[0]
                g = PCG(s1, s2)
                plain = bytes(a ^ b for a, b in zip(body, g.ks(len(body))))
                for kw in ({"uncompressed_size": declared}, {}):
                    try:
                        out = lz4.block.decompress(plain, **kw)
                        m = "MATCH" if out == dst else f"size={len(out)}"
                        print(f"  body@{body_off:>2} seed@{seed_off} -> {m}  {out[:16].hex()}")
                        break
                    except Exception:
                        pass


if __name__ == "__main__":
    main()
