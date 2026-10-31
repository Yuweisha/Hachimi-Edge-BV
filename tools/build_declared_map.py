"""生成本地服务器用的「声明体」：让 src[0:4] 精确等于 replay.bin 的 declared。

服务器按接口路径返回：
    [u32 declared][rest...]  共 40 字节
插件读到 declared 后直接命中 replay.bin。
"""
from __future__ import annotations

import glob
import json
import os
import struct
import sys

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
OUT = r"C:/Users/Schwarz/uma_replay/declared_map.json"


def main() -> int:
    files = sorted(glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack")))
    if not files:
        print("没找到 msgpack")
        return 1

    # 路径 -> declared（用 JSON 里的名字推断接口，或退回序号）
    mapping = {}
    for f in files:
        d = open(f, "rb").read()
        base = os.path.basename(f)
        # 名字形如 0000_start_session.msgpack
        name = base[5:-len(".msgpack")]
        # 去掉可能的序号前缀
        mapping.setdefault(name, []).append(len(d))

    # 同名多条时取最大
    final = {k: max(v) for k, v in mapping.items()}
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(final, fp, ensure_ascii=False, indent=2)

    print(f"写出 {OUT}，{len(final)} 条")
    for k, v in sorted(final.items())[:20]:
        print("  %-42s %10d" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
