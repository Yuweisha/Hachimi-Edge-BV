"""用落盘的密钥流块暴力解 trainer_note 的密文。"""
import base64
import glob
import os
import sys

import msgpack

RAW = r"C:/Users/Schwarz/uma_replay/raw/note_trainer_note.raw"
KSDIR = r"C:/Users/Schwarz/ksout"


def main() -> int:
    body = open(RAW, "rb").read()
    raw = base64.b64decode(body)
    print(f"trainer_note raw: {len(raw)} B")
    print(f"前 48 字节: {raw[:48].hex(' ')}")

    # 布局假设：[4B header][32B key][密文]
    ct = raw[36:]
    print(f"密文: {len(ct)} B")

    ks_files = sorted(glob.glob(os.path.join(KSDIR, "*.bin")))
    print(f"密钥流块: {len(ks_files)}")

    # 尝试每个块作为起点，连续取足够块
    need = (len(ct) + 15) // 16
    print(f"需要连续 {need} 块")

    # 先看块大小
    if ks_files:
        print("块大小:", os.path.getsize(ks_files[0]))

    hits = []
    for idx in range(len(ks_files) - need):
        try:
            stream = b"".join(open(ks_files[idx + i], "rb").read() for i in range(need))
        except Exception:
            continue
        if len(stream) < len(ct):
            continue
        pt = bytes(a ^ b for a, b in zip(ct, stream))
        # 合法 msgpack 开头：0x82-0x83 (fixmap) 或 0xde
        if pt[0] in (0x82, 0x83, 0xde):
            try:
                v = msgpack.unpackb(pt, raw=False, strict_map_key=False)
                hits.append((idx, v))
                print(f"\n命中 @ 块 {idx}: {list(v.keys())[:6]}")
                if len(hits) >= 3:
                    break
            except Exception:
                pass

    print(f"\n共 {len(hits)} 个命中")
    return 0


if __name__ == "__main__":
    sys.exit(main())
