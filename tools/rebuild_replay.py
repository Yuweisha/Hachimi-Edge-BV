"""从抓到的 *.msgpack 重建 replay.bin（供插件离线回放）。

格式：
    "RPLY" + u32 count
    每项: u32 src_size + u32 declared + u32 data_len + data

key 用 declared（明文长度），src_size 填 0 让 lookup 走 fallback。
"""
from __future__ import annotations

import glob
import os
import struct
import sys

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
OUT = r"C:/Users/Schwarz/uma_replay/replay.bin"


def main() -> int:
    files = sorted(glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack")))
    if not files:
        print("没找到 msgpack")
        return 1

    # 按 declared 去重，保留最大的
    best = {}
    for f in files:
        d = open(f, "rb").read()
        if len(d) < 8:
            continue
        declared = len(d)
        name = os.path.basename(f)
        if declared not in best or len(d) > len(best[declared][1]):
            best[declared] = (name, d)

    items = [(0, decl, data) for decl, (_, data) in sorted(best.items())]
    with open(OUT, "wb") as fp:
        fp.write(b"RPLY")
        fp.write(struct.pack("<I", len(items)))
        for src_size, declared, data in items:
            fp.write(struct.pack("<III", src_size, declared, len(data)))
            fp.write(data)

    print(f"共 {len(files)} 个 msgpack，去重后 {len(items)} 条")
    print(f"写出 {OUT} ({os.path.getsize(OUT)} B)")
    print()
    print("%-24s %10s" % ("NAME", "DECLARED"))
    for decl, (name, _) in sorted(best.items()):
        print("%-24s %10d" % (name[:24], decl))
    return 0


if __name__ == "__main__":
    sys.exit(main())
