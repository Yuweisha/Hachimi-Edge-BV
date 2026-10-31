"""穷举尝试解密 declared=0 的三个接口。

结构: [4B=0][32B 材料][密文]
假设: 32B 材料里藏着 key/iv/nonce
"""
import base64
import itertools
from pathlib import Path

from Crypto.Cipher import AES, ChaCha20, ChaCha20_Poly1305, Salsa20
from Crypto.Util.Padding import unpad

R = Path("C:/Users/Schwarz/uma_replay/raw")
SAMPLES = ["note_trainer_note", "note_save_voice", "jukebox_draw_random_request"]


def looks_like_msgpack(plain: bytes) -> bool:
    if not plain:
        return False
    b = plain[0]
    # fixmap 0x80-0x8f / fixarray 0x90-0x9f
    if 0x80 <= b <= 0x9F:
        # 检查 key 是否可打印
        printable = sum(1 for x in plain[:32] if 32 <= x < 127)
        return printable >= 8
    return False


def show(name: str, method: str, plain: bytes) -> None:
    ok = looks_like_msgpack(plain)
    print(f"  {'★★★' if ok else '   '} {method:<32} {plain[:56]!r}")
    if ok:
        print(f"       >>> 可能是明文! 全长 {len(plain)} B")


def try_all(name: str, mat: bytes, ct: bytes) -> None:
    print(f"\n=== {name} (mat={len(mat)}B, ct={len(ct)}B) ===")

    k16a, k16b = mat[:16], mat[16:]
    k32 = mat

    # --- AES-CBC，各种 key/iv 组合 ---
    for kname, key in (("k[0:16]", k16a), ("k[16:32]", k16b), ("k[0:32]", k32)):
        for iname, iv in (("iv=0", b"\x00" * 16), ("iv=k[0:16]", k16a), ("iv=k[16:32]", k16b)):
            if kname == "k[0:32]" and AES.block_size != 16:
                continue
            try:
                c = AES.new(key, AES.MODE_CBC, iv)
                p = c.decrypt(ct)
                try:
                    p2 = unpad(p, 16)
                    show(name, f"AES-CBC {kname} {iname} (pad OK)", p2)
                except Exception:
                    show(name, f"AES-CBC {kname} {iname}", p)
            except Exception:
                pass

    # --- AES-CTR（ctr 起点 0 / 前16B材料）---
    for kname, key in (("k[0:16]", k16a), ("k[16:32]", k16b), ("k[0:32]", k32)):
        for cname, nonce in (("ctr=0", b"\x00" * 16), ("ctr=k[0:16]", k16a), ("ctr=k[16:32]", k16b)):
            try:
                c = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=int.from_bytes(nonce, "big"))
                p = c.decrypt(ct)
                show(name, f"AES-CTR {kname} {cname}", p)
            except Exception:
                pass

    # --- AES-ECB ---
    for kname, key in (("k[0:16]", k16a), ("k[16:32]", k16b), ("k[0:32]", k32)):
        try:
            c = AES.new(key, AES.MODE_ECB)
            p = c.decrypt(ct[:len(ct) // 16 * 16])
            show(name, f"AES-ECB {kname}", p)
        except Exception:
            pass

    # --- ChaCha20 / Salsa20 ---
    for kname, key in (("k32", k32), ("k16+pad", k16a + b"\x00" * 16)):
        for nname, nonce in (("n=0(8)", b"\x00" * 8),
                             ("n=k[:8]", k32[:8]),
                             ("n=0(12)", b"\x00" * 12),
                             ("n=k[:12]", k32[:12])):
            if len(nonce) == 8:
                try:
                    c = Salsa20.new(key=key, nonce=nonce)
                    p = c.decrypt(ct)
                    show(name, f"Salsa20 {kname} {nname}", p)
                except Exception:
                    pass
            else:
                try:
                    c = ChaCha20.new(key=key, nonce=nonce)
                    p = c.decrypt(ct)
                    show(name, f"ChaCha20 {kname} {nname}", p)
                except Exception:
                    pass

    # --- ChaCha20-Poly1305（前 12B nonce + 后 16B tag）---
    for nname, nonce, body in (("n=ct[:12]", ct[:12], ct[12:]),
                               ("n=mat[:12]", k32[:12], ct)):
        try:
            c = ChaCha20_Poly1305.new(key=k32, nonce=nonce)
            p = c.decrypt_and_verify(body[:-16], body[-16:])
            show(name, f"ChaCha20-Poly1305 {nname} (VERIFY OK)", p)
        except Exception:
            pass

    # --- 直接看是不是明文（无加密）---
    show(name, "原样（未解密）", ct)


for s in SAMPLES:
    raw = (R / f"{s}.raw").read_bytes()
    try:
        b = base64.b64decode(raw.strip() + b"==")
    except Exception as e:
        print(f"{s}: b64 失败 {e}")
        continue
    if len(b) < 36:
        print(f"{s}: 太短 {len(b)}")
        continue
    mat, ct = b[4:36], b[36:]
    try_all(s, mat, ct)
