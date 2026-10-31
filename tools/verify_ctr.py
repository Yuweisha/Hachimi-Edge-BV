"""用 ctrsamples 验证 SHA-CTR 假设。

已知：
  - ctx+0x1a1 = 2  → SHA 族
  - keystream = plain XOR cipher
  - 计数器块在 ctx+0x180（16 字节）
  - 密钥区在 ctx+0xe0（32 字节，前 16 有值）
  - 计数器初值 ctx+0x18c

试各种 SHA 构造：
  SHAxxx(key || ctr), SHAxxx(ctr || key), SHAxxx(key || bswap(ctr)) ...
"""
from __future__ import annotations

import glob
import hashlib
import os
import struct

D = r"C:/Users/Schwarz/ctrsamples"


def load(idx: str):
    p2 = open(os.path.join(D, f"{idx}_p2_plain.bin"), "rb").read()
    p4 = open(os.path.join(D, f"{idx}_p4_cipher.bin"), "rb").read()
    e0 = open(os.path.join(D, f"{idx}_ctx_e0.bin"), "rb").read()
    b180 = open(os.path.join(D, f"{idx}_ctx_180.bin"), "rb").read()
    b60 = open(os.path.join(D, f"{idx}_ctx_60.bin"), "rb").read()
    return p2, p4, e0, b180, b60


def main():
    idxs = sorted({os.path.basename(f)[:2] for f in glob.glob(os.path.join(D, "*_p2_plain.bin"))})
    print(f"样本数: {len(idxs)}")

    for idx in idxs:
        p2, p4, e0, b180, b60 = load(idx)
        ks = bytes(a ^ b for a, b in zip(p2, p4))
        print(f"\n=== {idx}: len={len(p2)} ===")
        print(f"  plain[0:16]  = {p2[:16].hex()}")
        print(f"  cipher[0:16] = {p4[:16].hex()}")
        print(f"  keystream    = {ks[:16].hex()}")
        print(f"  ctx_e0[0:16] = {e0[:16].hex()}")
        print(f"  ctx_180      = {b180.hex()}")
        print(f"  ctx_60[0:16] = {b60[:16].hex()}")

        # 候选密钥
        keys = {
            "e0_0_16": e0[:16],
            "e0_0_32": e0,
            "e0_16_32": e0[16:],
            "b180": b180,
            "b60_0_16": b60[:16],
        }
        # 候选计数器块
        ctrs = {
            "b180": b180,
            "b180_be": b180[::-1],
            "b180_hi8": b180[:8],
            "b180_lo8": b180[8:],
            "zero16": b"\x00" * 16,
        }

        hit = False
        for kname, k in keys.items():
            for cname, c in ctrs.items():
                for algo in ("sha256", "sha1", "sha512", "md5"):
                    for order, data in (("k|c", k + c), ("c|k", c + k), ("k", k), ("c", c)):
                        h = hashlib.new(algo, data).digest()
                        if h[:16] == ks[:16]:
                            print(f"  ★★★ 命中 super: {algo} {order} key={kname} ctr={cname}")
                            hit = True
                        if h[::-1][:16] == ks[:16]:
                            print(f"  ★★★ 命中 rev:   {algo} {order} key={kname} ctr={cname}")
                            hit = True
        if not hit:
            print("  （单块构造全部未命中）")


if __name__ == "__main__":
    main()
