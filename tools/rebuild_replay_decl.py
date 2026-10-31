"""rebuild：key = declared（明文长度），服务器保证同路径同长度。"""
from __future__ import annotations

import glob
import os
import struct
import sys

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
OUT = r"C:/Users/Schwarz/uma_replay/replay.bin"


def main() -> int:
    files = sorted(glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack")))
    files += sorted(glob.glob(os.path.join(GD, "hachimi/http/*/*.json")))
    if not files:
        print("没找到数据")
        return 1

    best = {}
    for f in files:
        d = open(f, "rb").read()
        if len(d) < 8:
            continue
        # .json 是 pretty 版，跳过（避免长度不同）
        if f.endswith(".json"):
            continue
        if len(d) not in best or len(d) > len(best[len(d)][1]):
            best[len(d)] = (os.path.basename(f), d)

    items = [(decl, name, d) for decl, (name, d) in sorted(best.items())]
    with open(OUT, "wb") as fp:
        fp.write(b"RPLY")
        fp.write(struct.pack("<I", len(items)))
        for decl, name, data in items:
            fp.write(struct.pack("<III", decl, decl, len(data)))
            fp.write(data)

    print(f"写出 {OUT} ({os.path.getsize(OUT)} B)，{len(items)} 条（key=declared）")
    for decl, name, _ in items[:8]:
        print("  %-44s %10d" % (name[:44], decl))
    return 0


if __name__ == "__main__":
    sys.exit(main())
