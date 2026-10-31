"""用序号方案重建 replay.bin：key = 接口序号（0,1,2,...）。

顺序按抓包时的文件名序号（0000, 0001, ...）排。
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

    # 按文件名里的序号排序
    items = []
    for f in files:
        base = os.path.basename(f)
        try:
            seq = int(base[:4])
        except ValueError:
            continue
        d = open(f, "rb").read()
        if len(d) < 8:
            continue
        name = base[5:-len(".msgpack")]
        items.append((seq, name, d))

    items.sort(key=lambda x: x[0])

    # 同序号取最大（多次抓包会重号）
    best = {}
    for seq, name, d in items:
        if seq not in best or len(d) > len(best[seq][1]):
            best[seq] = (name, d)

    out_items = [(seq, name, d) for seq, (name, d) in sorted(best.items())]

    with open(OUT, "wb") as fp:
        fp.write(b"RPLY")
        fp.write(struct.pack("<I", len(out_items)))
        for seq, name, data in out_items:
            # src_size 填 seq（插件按序号查），declared 填长度
            fp.write(struct.pack("<III", seq, len(data), len(data)))
            fp.write(data)

    print(f"写出 {OUT} ({os.path.getsize(OUT)} B)，{len(out_items)} 条")
    print()
    print("%-6s %-40s %10s" % ("SEQ", "NAME", "LEN"))
    for seq, name, data in out_items:
        print("%-6d %-40s %10d" % (seq, name[:40], len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
