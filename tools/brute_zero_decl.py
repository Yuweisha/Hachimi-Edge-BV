"""用 ksnew 的密钥流暴力解 declared=0 的三个接口。"""
import base64
import glob
import os

import msgpack

RAW = r"C:/Users/Schwarz/uma_replay/raw"
KS = r"C:/Users/Schwarz/ksnew"

TARGETS = ["note_trainer_note", "note_save_voice", "jukebox_draw_random_request"]


def try_decode(name: str, ks_files: list[str]) -> None:
    body = open(os.path.join(RAW, name + ".raw"), "rb").read()
    try:
        raw = base64.b64decode(body)
    except Exception as e:
        print(f"{name}: base64 失败 {e}")
        return
    print(f"\n=== {name}: raw={len(raw)} B ===")
    print(f"  前 48: {raw[:48].hex(' ')}")

    # 尝试多种布局
    layouts = [
        ("[36:][:36]", raw[36:], raw[:36]),
        ("[4:][:4]", raw[4:], raw[:4]),
        ("[:][:]", raw, b""),
    ]

    for label, ct, hdr in layouts:
        if len(ct) < 8:
            continue
        need = (len(ct) + 15) // 16
        for start in range(max(0, len(ks_files) - 600), len(ks_files) - need):
            stream = b"".join(open(ks_files[start + i], "rb").read() for i in range(need))
            if len(stream) < len(ct):
                continue
            pt = bytes(a ^ b for a, b in zip(ct, stream))
            if pt and pt[0] in (0x82, 0x83, 0x81, 0xde, 0x80):
                try:
                    v = msgpack.unpackb(pt, raw=False, strict_map_key=False)
                    print(f"  ★ 命中 layout={label} start={start}")
                    print(f"     keys={list(v.keys())[:6]}")
                    return
                except Exception:
                    pass
    print("  未命中")


def main() -> int:
    ks_files = sorted(glob.glob(os.path.join(KS, "*.bin")))
    print(f"密钥流: {len(ks_files)} 块")
    if ks_files:
        print(f"  首块 {os.path.getsize(ks_files[0])} B, 尾块 {os.path.getsize(ks_files[-1])} B")
    for t in TARGETS:
        if os.path.exists(os.path.join(RAW, t + ".raw")):
            try_decode(t, ks_files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
