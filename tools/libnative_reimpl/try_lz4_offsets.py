"""用 0x143210 反汇编确认的标准 LZ4 block 格式，穷举 offset 与长度参数。

反汇编依据：
  token = src[i];  litlen = token >> 4;  若 ==15 则累加后续 0xff 链
  复制 litlen 字节；读 2 字节 LE offset；matchlen = (token & 0xf) + 4；
  若 (token & 0xf)==15 则累加后续 0xff 链（+0x13 已含 +15+4）
"""
from __future__ import annotations

import glob
import os
import struct

try:
    import lz4.block as lz4b
except ImportError:
    lz4b = None


def try_lz4(data: bytes, size: int):
    try:
        return lz4b.decompress(data, uncompressed_size=size)
    except Exception:
        return None


def main():
    pairs = sorted(glob.glob(r"C:/Users/Schwarz/umapairs/*_src.bin"))
    print(f"配对数 {len(pairs)}  lz4={'ok' if lz4b else 'MISSING'}\n")

    hit = 0
    for sp in pairs:
        src = open(sp, "rb").read()
        dp = sp.replace("_src.bin", "_dst.bin")
        if not os.path.exists(dp):
            continue
        dst = open(dp, "rb").read()
        declared = struct.unpack_from("<I", src, 0)[0]
        name = os.path.basename(sp)

        found = False
        # 偏移 0..40，长度参数用 declared / len(dst) / srcSize-36
        for off in range(0, 41):
            body = src[off:]
            for size in {declared, len(dst), len(src) - off, len(dst) + 64}:
                if size <= 0:
                    continue
                out = try_lz4(body, size)
                if out is None:
                    continue
                if out == dst:
                    print(f"★★★ MATCH {name}: off={off} size={size}")
                    hit += 1
                    found = True
                elif len(out) == len(dst):
                    same = sum(1 for a, b in zip(out, dst) if a == b)
                    if same > len(dst) * 0.9:
                        print(f"★ 近匹配 {name}: off={off} size={size} 相同 {same}/{len(dst)}")
                        found = True
        if not found:
            print(f"  {name}: src={len(src)} dst={len(dst)} declared={declared} 全部失败")

    print(f"\n命中 {hit}")


if __name__ == "__main__":
    main()
