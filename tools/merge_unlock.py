"""把解锁后的 read_info/index 合并进 replay.bin，并更新 path_declared。"""
from __future__ import annotations

import json
import struct
import sys

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
UNLOCKED = r"C:/Users/Schwarz/uma_replay/unlock/read_info_index.msgpack"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
OLD_LEN = 60361


def main() -> int:
    new_data = open(UNLOCKED, "rb").read()
    new_len = len(new_data)
    print(f"new read_info/index: {new_len} B")

    blob = open(REPLAY, "rb").read()
    assert blob[:4] == b"RPLY"
    n = struct.unpack_from("<I", blob, 4)[0]
    off = 8
    items = []
    for _ in range(n):
        src, decl, dl = struct.unpack_from("<III", blob, off)
        off += 12
        data = blob[off:off + dl]
        off += dl
        if decl == OLD_LEN:
            print(f"替换 declared={decl} ({dl} B) -> {new_len} B")
            items.append((new_len, new_data))
        else:
            items.append((decl, data))

    # 去掉重复（同长度只留一个）
    uniq = {}
    for d, data in items:
        uniq[d] = data
    items = sorted(uniq.items())

    out = bytearray(b"RPLY")
    out += struct.pack("<I", len(items))
    for decl, data in items:
        out += struct.pack("<III", decl, decl, len(data))
        out += data
    open(REPLAY, "wb").write(out)
    print(f"replay.bin 已写: {len(items)} 条, {len(out)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["read_info/index"] = new_len
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print(f"path_declared: read_info/index -> {new_len}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
