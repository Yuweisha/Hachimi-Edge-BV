"""用修正后的 PCG 解密 lz4pairs 里的样本，再试各种解压器。"""

import operator
import sys

sys.path.insert(0, "C:/Users/Schwarz/projects/Hachimi-Edge/tools")
from uma_pcg_decrypt import pcg_init_from_header, keystream

XOR = operator.xor


def try_decompress(data):
    """依次尝试常见解压器，返回 (名字, 结果) 或 None。"""
    # 标准 LZ4 block
    try:
        import lz4.block

        for size in (None, len(data) * 20):
            try:
                out = lz4.block.decompress(data, uncompressed_size=size or 0)
                return "lz4", out
            except Exception:
                pass
    except ImportError:
        pass
    # zstd
    try:
        import zstandard as zstd

        out = zstd.ZstdDecompressor().decompress(data, max_output_size=len(data) * 50)
        return "zstd", out
    except Exception:
        pass
    # brotli
    try:
        import brotli

        out = brotli.decompress(data)
        return "brotli", out
    except Exception:
        pass
    # raw deflate
    try:
        import zlib

        out = zlib.decompress(data, -15)
        return "deflate-raw", out
    except Exception:
        pass
    return None


def main():
    for i in range(4):
        src = open("C:/FiddlerDump/lz4pairs/%03d_src.bin" % i, "rb").read()
        dst = open("C:/FiddlerDump/lz4pairs/%03d_dst.bin" % i, "rb").read()
        print("\n=== #%d src=%d dst=%d ===" % (i, len(src), len(dst)))

        best = None
        for seed_off in (4,):
            state, inc = pcg_init_from_header(src[seed_off:seed_off + 16])
            for data_off in (20, 36, 44, 24, 32, 40):
                if data_off >= len(src):
                    continue
                ks, _ = keystream(state, inc, len(src) - data_off)
                plain = bytes(map(XOR, src[data_off:], ks))
                res = try_decompress(plain)
                if res:
                    name, out = res
                    ok = out == dst
                    print("   seed=%d data=%d -> %s %d bytes match=%s"
                          % (seed_off, data_off, name, len(out), ok))
                    if ok:
                        best = (seed_off, data_off, name)
                        break
            if best:
                break

        if not best:
            # 至少展示解密后的熵特征
            state, inc = pcg_init_from_header(src[4:20])
            for data_off in (36,):
                ks, _ = keystream(state, inc, min(64, len(src) - data_off))
                plain = bytes(map(XOR, src[data_off:data_off + 64], ks))
                print("   data=%d 解密头: %s" % (data_off, plain[:32].hex(" ")))
        else:
            print("   ★★★ 命中: seed_off=%d data_off=%d 解压器=%s" % best)


if __name__ == "__main__":
    main()
