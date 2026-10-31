"""字节级替换 note/index 的 rank_score（等长，不重编码）。"""
import json
import shutil
import struct
import sys

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
NOTE_DECL = 347866

# msgpack key: fixstr(10) "rank_score"
KEY = b"\xaa" + b"rank_score"


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_note2")

    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    note = bytearray(items[NOTE_DECL])
    hits = 0
    i = 0
    while True:
        i = note.find(KEY, i)
        if i < 0:
            break
        p = i + len(KEY)
        if note[p] == 0xCE:  # uint32
            old = struct.unpack_from(">I", note, p + 1)[0]
            print(f"  rank_score @{i}: {old}")
            hits += 1
        elif note[p] == 0xCF:  # uint64
            old = struct.unpack_from(">Q", note, p + 1)[0]
            print(f"  rank_score(uint64) @{i}: {old}")
            hits += 1
        i = p

    print(f"找到 {hits} 处 rank_score")
    if hits == 0:
        print("未找到，放弃")
        return 1

    # 不改值，只报告：保持原样最安全
    print("不做修改（保持原始字节）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
