"""搜 10950450 / 11285 在 msgpack 里的所有编码形式。"""
from __future__ import annotations

import glob
import os
import struct

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"

NUMS = [10950450, 11285]


def variants(n: int):
    out = {}
    if n <= 0x7F:
        out["fixint"] = bytes([n])
    if n <= 0xFF:
        out["uint8"] = b"\xcc" + bytes([n])
    if n <= 0xFFFF:
        out["uint16"] = b"\xcd" + struct.pack(">H", n)
    if n <= 0xFFFFFFFF:
        out["uint32"] = b"\xce" + struct.pack(">I", n)
    out["uint64"] = b"\xcf" + struct.pack(">Q", n)
    if n <= 0x7FFFFFFF:
        out["int32"] = b"\xd2" + struct.pack(">i", n)
    out["int64"] = b"\xd3" + struct.pack(">q", n)
    out["ascii"] = str(n).encode()
    return out


def main() -> int:
    files = sorted(glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack")),
                   key=os.path.getsize, reverse=True)[:3]
    if not files:
        print("没有 msgpack")
        return 1

    for f in files:
        d = open(f, "rb").read()
        print(f"\n{os.path.basename(f)} ({len(d)} B)")
        for n in NUMS:
            hits = []
            for name, pat in variants(n).items():
                c = d.count(pat)
                if c:
                    hits.append(f"{name}x{c}")
            print("  %-10d %s" % (n, ", ".join(hits) if hits else "未找到"))

    # 同时在 json 里找
    js = sorted(glob.glob(os.path.join(GD, "hachimi/http/*/*.json")),
                key=os.path.getsize, reverse=True)[:3]
    for f in js:
        t = open(f, "rb").read()
        print(f"\n{os.path.basename(f)} ({len(t)} B)")
        for n in NUMS:
            print("  %-10d x%d" % (n, t.count(str(n).encode())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
