"""扩大穷举：32B 材料的各种切分 x 各种算法 x 严格 msgpack 判定。"""
import base64
import itertools
from pathlib import Path

from Crypto.Cipher import AES, ChaCha20, Salsa20, ARC2, ARC4, Blowfish, CAST, DES, DES3

R = Path("C:/Users/Schwarz/uma_replay/raw")
SAMPLES = ["note_trainer_note", "note_save_voice", "jukebox_draw_random_request"]


def strict_msgpack(plain: bytes) -> bool:
    """严格判定：首字节必须是 fixmap(0x80-0x8f)，紧跟的 key 必须可打印。"""
    if len(plain) < 8:
        return False
    b = plain[0]
    if not (0x80 <= b <= 0x8F):
        return False
    # 下一个字节应是 fixstr 长度
    n = plain[1]
    if not (0xA0 <= n <= 0xBF):
        return False
    klen = n - 0xA0
    if klen == 0 or len(plain) < 2 + klen:
        return False
    key = plain[2:2 + klen]
    return all(32 <= c < 127 for c in key)


def report(name, method, plain):
    if strict_msgpack(plain):
        print(f"  ★★★ {method:<44} {plain[:64]!r}")


def slices32(m: bytes):
    """32 字节材料的所有合理切分。"""
    out = []
    # key 长度 16 or 32
    for klen in (16, 32):
        for kstart in (0, 32 - klen):
            key = m[kstart:kstart + klen]
            rest = [m[i] for i in range(32) if not (kstart <= i < kstart + klen)]
            out.append((f"k=[{kstart}:{kstart+klen}]", key, bytes(rest)))
    return out


def try_everything(name, mat, ct):
    print(f"\n=== {name} (mat=32 ct={len(ct)}) ===")
    found = False

    for kname, key, rest in slices32(mat):
        # rest 可能是 16 字节（当 key 16）或 0（当 key 32）
        # --- ChaCha20 / Salsa20 ---
        if len(key) == 32:
            for nname, nonce in (("n=0", b"\x00" * 8), ("n=mat0:8", mat[:8]), ("n=mat24:32", mat[24:32])):
                try:
                    p = Salsa20.new(key=key, nonce=nonce).decrypt(ct)
                    report(name, f"Salsa20 {kname} {nname}", p)
                except Exception:
                    pass
            for nname, nonce in (("n=0", b"\x00" * 12), ("n=mat0:12", mat[:12]), ("n=mat20:32", mat[20:32])):
                try:
                    p = ChaCha20.new(key=key, nonce=nonce).decrypt(ct)
                    report(name, f"ChaCha20 {kname} {nname}", p)
                except Exception:
                    pass

        # --- AES-CBC / CTR / ECB ---
        for kname2, key2 in ((kname, key if len(key) in (16, 24, 32) else None),):
            pass

        if len(key) == 16:
            for ivname, iv in (("iv=rest", rest), ("iv=0", b"\x00" * 16), ("iv=mat16:32", mat[16:32])):
                if len(iv) != 16:
                    continue
                try:
                    p = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
                    report(name, f"AES-CBC {kname} {ivname}", p)
                    if len(p) >= 16:
                        p2 = p[:-p[-1]] if 1 <= p[-1] <= 16 else p
                        report(name, f"AES-CBC {kname} {ivname} unpad", p2)
                except Exception:
                    pass
                try:
                    p = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=int.from_bytes(iv, "big")).decrypt(ct)
                    report(name, f"AES-CTR {kname} {ivname}", p)
                except Exception:
                    pass
            try:
                p = AES.new(key, AES.MODE_ECB).decrypt(ct[:len(ct) // 16 * 16])
                report(name, f"AES-ECB {kname}", p)
            except Exception:
                pass

    # --- 其他经典算法（key=16 取 mat[0:16]）---
    k16 = mat[:16]
    for cls, nm in ((Blowfish, "Blowfish"), (CAST, "CAST"), (DES, "DES")):
        try:
            c = cls.new(k16, cls.MODE_ECB)
            p = c.decrypt(ct[:len(ct) // 8 * 8])
            report(name, f"{nm}-ECB k16", p)
        except Exception:
            pass
    try:
        p = ARC4.new(k16).decrypt(ct)
        report(name, "RC4 k16", p)
    except Exception:
        pass

    # --- 简单 XOR ---
    for klen in (16, 32):
        key = mat[:klen]
        p = bytes(ct[i] ^ key[i % klen] for i in range(len(ct)))
        report(name, f"XOR k{klen}", p)

    print("  （只有 ★★★ 才是严格 msgpack 命中）")


for s in SAMPLES:
    raw = (R / f"{s}.raw").read_bytes()
    b = base64.b64decode(raw.strip() + b"==")
    try_everything(s, b[4:36], b[36:])
