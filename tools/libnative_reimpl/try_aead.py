"""AES-GCM / ChaCha20-Poly1305 全面尝试（含字节序反转）。

依据：
  * RVA 0x3a18d0..0x3a1910 的 64 字节硬编码常量
  * 0x3180 对它们做了 8 字节反转（bswap8）
  * src 头 36 字节 = 4 长度 + 12 nonce + 16 tag + 4
  * src[36:] 密文，长度 == 明文长度（GCM/ChaCha 都是流模式）
  * TLS 套件表里有 AES-256-GCM / AES-128-GCM / ChaCha20-Poly1305
"""
from __future__ import annotations

import glob
import os
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

K = bytes.fromhex(
    "2b50db38eb3fbc66aa2230e6a6b22463"
    "47d6a7cb48f91358ed97d7e58c7ec590"
    "0125b00ec014923c7ff806bc7c87f938"
    "1dab7ca01ecfe92dc36dadba62549a66"
)


def bswap8(b: bytes) -> bytes:
    out = bytearray(len(b))
    for i in range(0, len(b) - 7, 8):
        out[i:i + 8] = b[i:i + 8][::-1]
    return bytes(out)


def bswap4(b: bytes) -> bytes:
    out = bytearray(len(b))
    for i in range(0, len(b) - 3, 4):
        out[i:i + 4] = b[i:i + 4][::-1]
    return bytes(out)


def key_candidates():
    """所有可能的 16/32 字节密钥。"""
    seen = {}

    def add(name, b):
        if len(b) in (16, 24, 32) and b not in seen:
            seen[b] = name

    variants = {
        "K": K,
        "bs8": bswap8(K),
        "bs4": bswap4(K),
        "rev": K[::-1],
    }
    for vn, v in variants.items():
        for off in range(0, len(v) - 15):
            add(f"{vn}[{off}:{off+16}]", v[off:off + 16])
        for off in range(0, len(v) - 31):
            add(f"{vn}[{off}:{off+32}]", v[off:off + 32])
    # 两两拼接
    parts = [K[i:i + 16] for i in range(0, 64, 16)]
    for i in range(4):
        for j in range(4):
            add(f"K[{i}]+K[{j}]", parts[i] + parts[j])
    return seen


def main():
    pairs = sorted(glob.glob(r"C:/Users/Schwarz/umapairs/*_src.bin"))
    if not pairs:
        print("没有配对")
        return

    keys = key_candidates()
    print(f"密钥候选 {len(keys)} 个")

    # 头切分方案
    layouts = []
    for nonce_off, nonce_len in ((4, 12), (4, 8), (8, 12), (4, 16)):
        for tag_off, tag_len in ((16, 16), (20, 16), (32, 16)):
            for ct_off in (36, 32, 20):
                layouts.append((nonce_off, nonce_len, tag_off, tag_len, ct_off))
    print(f"头布局方案 {len(layouts)} 个\n")

    hits = 0
    tried = 0
    for sp in pairs[:4]:                     # 先跑前 4 组
        src = open(sp, "rb").read()
        dp = sp.replace("_src.bin", "_dst.bin")
        dst = open(dp, "rb").read()
        declared = struct.unpack_from("<I", src, 0)[0] or len(dst)
        name = os.path.basename(sp)

        for (no, nl, to, tl, co) in layouts:
            if co > len(src):
                continue
            nonce = src[no:no + nl]
            tag = src[to:to + tl]
            ct = src[co:]
            ct_tag = ct + tag

            for key, kname in keys.items():
                for alg_name, alg in (("AESGCM", AESGCM), ("ChaCha", ChaCha20Poly1305)):
                    if alg is ChaCha20Poly1305 and len(key) != 32:
                        continue
                    try:
                        out = alg(key).decrypt(nonce, ct_tag, None)
                    except Exception:
                        tried += 1
                        continue
                    tried += 1
                    ok = out == dst
                    if ok:
                        hits += 1
                        print(f"★★★ MATCH: {name} {alg_name} key={kname} "
                              f"nonce@{no}+{nl} tag@{to}+{tl} ct@{co}")
                        print(f"    {out[:32].hex()}")
                    else:
                        print(f"★ 解密成功但内容不同: {name} {alg_name} {kname} len={len(out)}")
    print(f"\n尝试 {tried:,} 次，命中 {hits}")


if __name__ == "__main__":
    main()
