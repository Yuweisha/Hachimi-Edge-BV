"""暴力搜索解密参数：seed 偏移 / 数据偏移，用 LZ4 合法性 + 长度匹配作为判据。"""
import base64
import glob
import operator
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from uma_pcg_decrypt import pcg_init_from_header, keystream

XOR = operator.xor


def lz4_block(src):
    """标准 LZ4 block 解压，失败返回 None。"""
    dst = bytearray()
    i, n = 0, len(src)
    while i < n:
        tok = src[i]
        i += 1
        lit = tok >> 4
        if lit == 15:
            while True:
                if i >= n:
                    return None
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        if i + lit > n:
            return None
        dst += src[i:i + lit]
        i += lit
        if i >= n:
            break
        if i + 2 > n:
            return None
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0 or off > len(dst):
            return None
        ml = tok & 0xF
        if ml == 15:
            while True:
                if i >= n:
                    return None
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        st = len(dst) - off
        for k in range(ml):
            dst.append(dst[st + k])
    return bytes(dst)


def parse(f):
    txt = open(f, "r", encoding="ascii", errors="ignore").read()
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


def main():
    found_any = False
    for f in sorted(glob.glob("C:/FiddlerDump/*.txt")):
        d = parse(f)
        b64 = d.get("RSPB64", "")
        if not b64:
            continue
        raw = base64.b64decode(b64 + "=" * ((4 - len(b64) % 4) % 4))
        if len(raw) < 40:
            continue
        declared = struct.unpack_from("<I", raw, 0)[0]
        name = os.path.basename(f)
        print("\n=== %s  raw=%d declared=%d ===" % (name, len(raw), declared))
        hit = False
        for seed_off in (4, 20, 0, 8, 12):
            if seed_off + 16 > len(raw):
                continue
            state0, inc = pcg_init_from_header(raw[seed_off:seed_off + 16])
            for data_off in range(16, 56):
                if data_off >= len(raw):
                    break
                body = raw[data_off:]
                ks, _ = keystream(state0, inc, len(body))
                plain = bytes(map(XOR, body, ks))
                out = lz4_block(plain)
                if out is not None and len(out) == declared:
                    print("  ★ 命中 seed_off=%d data_off=%d -> %d 字节" % (seed_off, data_off, len(out)))
                    print("    head:", out[:40].hex(" "))
                    print("    text:", "".join(chr(c) if 32 <= c < 127 else "." for c in out[:60]))
                    hit = True
                    found_any = True
                    break
            if hit:
                break
        if not hit:
            print("  未命中")
    print("\n总体:", "有结果" if found_any else "全部未命中")


if __name__ == "__main__":
    main()
