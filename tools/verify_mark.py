"""验证 mark_local 逻辑：把 msgpack 里的 10950450 / 11285 换成 100000000。"""
from __future__ import annotations

import glob
import os
import struct
import sys

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"

TARGETS = {10950450: b"\xce\x05\xf5\xe1\x00", 11285: b"\xce\x05\xf5\xe1\x00"}


def mp_size(d: bytes, i: int):
    b = d[i]
    if 0x00 <= b <= 0x7F or 0xE0 <= b <= 0xFF or b in (0xC0, 0xC2, 0xC3):
        return 1
    if 0x80 <= b <= 0x8F:
        return mp_container(d, i, b & 0x0F, 2)
    if 0x90 <= b <= 0x9F:
        return mp_container(d, i, b & 0x0F, 1)
    if 0xA0 <= b <= 0xBF:
        return 1 + (b & 0x1F)
    if b in (0xC4, 0xD9):
        return 2 + d[i + 1]
    if b in (0xC5, 0xDA):
        return 3 + struct.unpack_from(">H", d, i + 1)[0]
    if b in (0xC6, 0xDB):
        return 5 + struct.unpack_from(">I", d, i + 1)[0]
    if b == 0xC7:
        return 3 + d[i + 1]
    if b == 0xC8:
        return 4 + struct.unpack_from(">H", d, i + 1)[0]
    if b == 0xC9:
        return 6 + struct.unpack_from(">I", d, i + 1)[0]
    if b in (0xCA, 0xCE, 0xD2):
        return 5
    if b in (0xCB, 0xCF, 0xD3):
        return 9
    if b in (0xCC, 0xD0):
        return 2
    if b in (0xCD, 0xD1):
        return 3
    if b == 0xD4:
        return 3
    if b == 0xD5:
        return 4
    if b == 0xD6:
        return 6
    if b == 0xD7:
        return 10
    if b == 0xD8:
        return 18
    if b in (0xDC, 0xDE):
        return 3
    if b in (0xDD, 0xDF):
        return 5
    raise ValueError(f"unknown 0x{b:02x} at {i}")


def mp_container(d: bytes, i: int, cnt: int, items_per: int):
    b = d[i]
    if 0x80 <= b <= 0x8F or 0x90 <= b <= 0x9F:
        count = cnt
        hdr = 1
    elif b in (0xDC, 0xDE):
        count = struct.unpack_from(">H", d, i + 1)[0]
        hdr = 3
    else:
        count = struct.unpack_from(">I", d, i + 1)[0]
        hdr = 5
    p = i + hdr
    for _ in range(count * items_per):
        p += mp_size(d, p)
    return p - i


def rewrite(d: bytes, i: int, out: bytearray):
    b = d[i]
    sz = mp_size(d, i)

    if b == 0xCE and sz == 5:
        v = struct.unpack_from(">I", d, i + 1)[0]
        if v in TARGETS:
            out += TARGETS[v]
            return sz
    if b == 0xCD and sz == 3:
        v = struct.unpack_from(">H", d, i + 1)[0]
        if v in TARGETS:
            out += TARGETS[v]
            return sz

    is_map = 0x80 <= b <= 0x8F or b in (0xDE, 0xDF)
    is_arr = 0x90 <= b <= 0x9F or b in (0xDC, 0xDD)
    if is_map or is_arr:
        if 0x80 <= b <= 0x8F or 0x90 <= b <= 0x9F:
            hdr, count = 1, b & 0x0F
        elif b in (0xDC, 0xDE):
            hdr, count = 3, struct.unpack_from(">H", d, i + 1)[0]
        else:
            hdr, count = 5, struct.unpack_from(">I", d, i + 1)[0]
        out += d[i:i + hdr]
        p = i + hdr
        for _ in range(count * (2 if is_map else 1)):
            p += rewrite(d, p, out)
        return p - i

    out += d[i:i + sz]
    return sz


def main() -> int:
    files = sorted(glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack")),
                   key=os.path.getsize, reverse=True)
    if not files:
        print("没有 msgpack")
        return 1

    ok = 0
    for f in files[:5]:
        d = open(f, "rb").read()
        out = bytearray()
        try:
            used = rewrite(d, 0, out)
        except Exception as e:
            print("  %-40s 解析失败: %s" % (os.path.basename(f)[:40], e))
            continue
        if used != len(d):
            print("  %-40s 长度不符 used=%d len=%d" % (os.path.basename(f)[:40], used, len(d)))
            continue
        n1 = d.count(b"\xce\x00\xa7\x1c\xb2")
        n2 = d.count(b"\xcd\x2c\x15")
        changed = len(out) != len(d)
        print("  %-40s %8d B  10950450x%d 11285x%d  输出 %d B %s" % (
            os.path.basename(f)[:40], len(d), n1, n2, len(out),
            "已替换" if changed else "无变化"))
        if changed:
            ok += 1

    print(f"\n可替换样本: {ok}/{min(5, len(files))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
