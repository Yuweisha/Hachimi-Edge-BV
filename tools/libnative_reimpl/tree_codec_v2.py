"""Tree codec v2: try the bignum-tree hypothesis end to end.

Evidence gathered so far:
  * 0x3bbc0 does `a mod m` using subtract loops (no hardware div)
  * 0x46e60 does multi-precision dst += src * scalar
  * 0x472f0 does long division
  * 0x3ceb0 builds a binary tree of 48-byte nodes (left/right/parent, 16 B each)
  * 0x3d200 walks pairs, marking the midpoint
  * 0x3e180 splits into 16 or 32 blocks depending on input > 383 bytes
  * 0x173210 at the bottom is a standard LZ4 block decoder

The natural reading of "add / mul / div / mod + binary tree + block split" is a
modular exponentiation ladder, where each tree level squares and conditionally
multiplies by the base. Python's pow(base, exp, mod) does this natively, so this
module tests whether feeding such a transform into LZ4 reproduces the samples.

Several parameter hypotheses are tried because the exact moduli/offsets are not
yet pinned down.
"""

from __future__ import annotations

import struct

import lz4.block

from pcg_keystream import PCG32

MASK8 = 0xFF


def try_lz4(data: bytes, declared: int):
    """0x173210 is a standard LZ4 block decoder."""
    for kwargs in ({"uncompressed_size": declared}, {}):
        try:
            return lz4.block.decompress(data, **kwargs)
        except Exception:
            continue
    return None


def keystream_variants(payload: bytes):
    """Yield (name, data) candidates for the decrypted LZ4 stream."""
    # seeds read exactly as 0x33180 does
    pcg = PCG32.from_bytes(payload, 0)

    for skip in (0, 8, 10, 16, 32):
        body = payload[skip:]
        if not body:
            continue

        # A: pure PCG XOR
        g = PCG32.from_bytes(payload, 0)
        yield f"pcg-xor/skip{skip}", bytes(a ^ b for a, b in zip(body, g.keystream(len(body))))

        # B: PCG u64 XOR
        g = PCG32.from_bytes(payload, 0)
        yield f"pcg-u64/skip{skip}", bytes(a ^ b for a, b in zip(body, g.keystream_u64(len(body))))

        # C: modular ladder over the first seed u64, modulus = declared
        try:
            seed = struct.unpack_from("<Q", payload, 0)[0]
            mod = struct.unpack_from("<Q", payload, 8)[0] | 1
            if mod > 1:
                # each output byte = (seed ^ (base**i mod mod)) & 0xff
                ks = bytearray()
                acc = seed % mod
                base = 0x5851F42D4C957F2D % mod
                for i in range(len(body)):
                    ks.append(acc & MASK8)
                    acc = (acc * base) % mod
                yield f"modladder/skip{skip}", bytes(a ^ b for a, b in zip(body, ks))
        except Exception:
            pass

        # D: PCG seeded by MD5-like fold of the seed
        try:
            s = struct.unpack_from("<Q", payload, 0)[0]
            g = PCG32(s, (s >> 17) | 1)
            yield f"pcg-fold/skip{skip}", bytes(a ^ b for a, b in zip(body, g.keystream(len(body))))
        except Exception:
            pass


def main():
    import glob
    import os

    print(f'{"sample":16s} {"variant":24s} {"lz4":8s} {"out":>10s} {"dst":>10s}  head')
    print("-" * 96)

    hits = 0
    for p in sorted(glob.glob(r"C:/FiddlerDump/lz4pairs/*_src.bin")):
        src = open(p, "rb").read()
        if len(src) < 12:
            continue
        declared = struct.unpack_from("<I", src, 0)[0]
        if declared == 0:
            continue
        payload = src[4:]
        name = os.path.basename(p)

        dst_p = p.replace("_src.bin", "_dst.bin")
        dst = open(dst_p, "rb").read() if os.path.exists(dst_p) else b""

        for vname, data in keystream_variants(payload):
            out = try_lz4(data, declared)
            if out is None:
                continue
            matched = out == dst
            if matched:
                hits += 1
            print(f'{name:16s} {vname:24s} {"MATCH" if matched else "ok":8s} '
                  f'{len(out):>10,} {len(dst):>10,}  {out[:16].hex()}')

    print(f"\n命中 {hits} 组")


if __name__ == "__main__":
    main()
