"""用 ctrsamples（in/out/e0/b180/b60）验证 SHA-CTR。

keystream = in XOR out
计数器块 b180（16B），密钥区 e0（32B）
"""
from __future__ import annotations

import glob
import hashlib
import os

D = r"C:/Users/Schwarz/ctrsamples"


def load(idx):
    f = lambda s: open(os.path.join(D, f"{idx}_{s}.bin"), "rb").read()
    return f("in"), f("out"), f("e0"), f("b180"), f("b60")


def main():
    idxs = sorted({os.path.basename(f)[:2] for f in glob.glob(os.path.join(D, "*_in.bin"))})
    print(f"样本 {len(idxs)} 组\n")

    for idx in idxs:
        i, o, e0, b180, b60 = load(idx)
        ks = bytes(a ^ b for a, b in zip(i, o))
        print(f"=== {idx}: len={len(i)} ===")
        print(f"  in [:16] = {i[:16].hex()}")
        print(f"  out[:16] = {o[:16].hex()}")
        print(f"  ks [:16] = {ks[:16].hex()}")
        print(f"  e0 [:16] = {e0[:16].hex()}")
        print(f"  b180    = {b180.hex()}")
        print(f"  b60[:16]= {b60[:16].hex()}")

        keys = {"e0_16": e0[:16], "e0_32": e0, "e0_16b": e0[16:], "b180": b180, "b60_16": b60[:16]}
        ctrs = {"b180": b180, "b180r": b180[::-1], "hi8": b180[:8], "lo8": b180[8:], "zero": b"\0" * 16}

        hit = False
        for kn, k in keys.items():
            for cn, c in ctrs.items():
                for algo in ("sha256", "sha1", "sha512", "md5", "sha224", "sha384"):
                    for on, data in (("k|c", k + c), ("c|k", c + k), ("k", k), ("c", c),
                                     ("k%c", k + b"\0" + c), ("c%k", c + b"\0" + k)):
                        h = hashlib.new(algo, data).digest()
                        for tag, cand in (("fwd", h[:16]), ("rev", h[::-1][:16])):
                            if cand == ks[:16]:
                                print(f"  ★★★ HIT {algo} {on} {tag} key={kn} ctr={cn}")
                                hit = True
        if not hit:
            print("  （未命中）")
        print()


if __name__ == "__main__":
    main()
