"""用真实 (src, lz4in) 配对定位密钥流算法。

已知：
  src[0:4]   = 明文长度 LE
  src[4:36]  = 32 字节密钥材料
  src[36:]   = 加密后的 LZ4 流
  lz4in      = 解密后的 LZ4 流（长度 == len(src) - 36）
  keystream  = lz4in XOR src[36:]   （每次不同，说明有状态）
"""
from __future__ import annotations

import json
import os
import struct

MULT = 0x5851F42D4C957F2D


def load_pairs():
    out = []
    for n in ("0", "1"):
        sf = f"C:/Users/Schwarz/lz4in/{n}_src.bin"
        lf = f"C:/Users/Schwarz/lz4in/{n}.bin"
        if not (os.path.exists(sf) and os.path.exists(lf)):
            continue
        s = open(sf, "rb").read()
        lz = open(lf, "rb").read()
        if len(s) - len(lz) != 36:
            continue
        out.append((n, s, lz))
    return out


def keystream(src: bytes, lz: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(lz, src[36:36 + len(lz)]))


def pcg_stream(seed16: bytes, n: int) -> bytes:
    """SPEC 里的精确初始化：inc = BE64(seed[8:16])*2+1，state = BE64(seed[0:8])*M + inc*(M+1)。"""
    a = int.from_bytes(seed16[0:8], "little")
    b = int.from_bytes(seed16[8:16], "little")
    inc = (b << 1) | 1
    state = (a * MULT + inc * (MULT + 1)) & 0xFFFFFFFFFFFFFFFF
    out = bytearray()
    for _ in range(n):
        old = state
        state = (old * MULT + inc) & 0xFFFFFFFFFFFFFFFF
        x = (((old >> 45) ^ (old >> 27)) & 0xFFFFFFFF)
        rot = (old >> 59) & 0x1F
        v = ((x << ((-rot) & 0x1F)) | (x >> rot)) & 0xFFFFFFFF
        out.append(v & 0xFF)
    return bytes(out)


def pcg_variants(seed16: bytes, n: int):
    """多种初始化/输出变体。"""
    res = {}
    for endian in ("little", "big"):
        a = int.from_bytes(seed16[0:8], endian)
        b = int.from_bytes(seed16[8:16], endian)
        for init_name, state0, inc in (
            ("spec", (a * MULT + ((b << 1) | 1) * (MULT + 1)) & 0xFFFFFFFFFFFFFFFF, (b << 1) | 1),
            ("plain", a, (b << 1) | 1),
            ("swap", b, (a << 1) | 1),
            ("noadv", (a + ((b << 1) | 1)) & 0xFFFFFFFFFFFFFFFF, (b << 1) | 1),
        ):
            for outmode in ("low8", "xsh_rr_full", "high8"):
                st = state0
                buf = bytearray()
                for _ in range(n):
                    old = st
                    st = (old * MULT + inc) & 0xFFFFFFFFFFFFFFFF
                    x = (((old >> 45) ^ (old >> 27)) & 0xFFFFFFFF)
                    rot = (old >> 59) & 0x1F
                    v = ((x << ((-rot) & 0x1F)) | (x >> rot)) & 0xFFFFFFFF
                    if outmode == "low8":
                        buf.append(v & 0xFF)
                    elif outmode == "high8":
                        buf.append((v >> 24) & 0xFF)
                    else:
                        buf.extend(v.to_bytes(4, "little"))
                res[f"pcg_{endian}_{init_name}_{outmode}"] = bytes(buf[:n])
    return res


def aes_ctr_variants(key32: bytes, n: int):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    res = {}
    for nonce_name, nonce, ctr in (
        ("zero16", b"\x00" * 16, 0),
        ("len16", None, 0),
    ):
        if nonce is None:
            continue
        try:
            c = Cipher(algorithms.AES(key32), modes.CTR(nonce))
            e = c.encryptor()
            res[f"aesctr_{nonce_name}"] = e.update(b"\x00" * n)
        except Exception:
            pass
    return res


def chacha_variants(key32: bytes, n: int):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
    res = {}
    try:
        c = Cipher(algorithms.ChaCha20(key32, b"\x00" * 16), mode=None)
        e = c.encryptor()
        res["chacha_zero"] = e.update(b"\x00" * n)
    except Exception:
        pass
    return res


def score(name: str, guess: bytes, target: bytes) -> tuple[float, int]:
    m = min(len(guess), len(target))
    if m == 0:
        return 0.0, 0
    same = sum(1 for i in range(m) if guess[i] == target[i])
    return same / m, same


def main():
    pairs = load_pairs()
    print(f"配对数 {len(pairs)}")
    if not pairs:
        return

    results = []
    for tag, src, lz in pairs:
        keymat = src[4:36]
        ks = keystream(src, lz)
        n = min(len(ks), 4096)
        target = ks[:n]
        print(f"\n=== #{tag} src={len(src)} lz4in={len(lz)} ks[0:8]={ks[:8].hex()} ===")

        cands = {}
        # 32 字节材料：前/后/交错
        cands.update(pcg_variants(keymat[0:16], n))
        cands.update(pcg_variants(keymat[16:32], n))
        cands.update(aes_ctr_variants(keymat, n))
        cands.update(chacha_variants(keymat, n))
        # 明文长度参与
        cands.update(pcg_variants(src[0:4] + keymat[0:12], n))

        best = sorted(
            ((score(name, g, target)[0], name) for name, g in cands.items()),
            reverse=True,
        )[:5]
        for sc, name in best:
            results.append((tag, name, round(sc, 4)))
            print(f"  {sc*100:5.1f}%  {name}")

    print("\n=== 汇总最高 ===")
    for r in sorted(results, key=lambda x: -x[2])[:10]:
        print(f"  {r[2]*100:5.1f}%  {r[1]}  (样本 {r[0]})")


if __name__ == "__main__":
    main()
