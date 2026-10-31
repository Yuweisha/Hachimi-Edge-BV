"""同步 note/index 的关键字段到 load/index，避免游戏比对时报错。"""
import json
import shutil
import struct
import sys

import msgpack

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
LOAD_DECL = 1279656
NOTE_DECL = 347866


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_note")

    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    if LOAD_DECL not in items or NOTE_DECL not in items:
        print("缺少必要条目")
        return 1

    load = msgpack.unpackb(items[LOAD_DECL], raw=False, strict_map_key=False)["data"]
    note = msgpack.unpackb(items[NOTE_DECL], raw=False, strict_map_key=False)
    nd = note["data"]

    print("note/index 原有字段:", list(nd.keys()))

    # 同步这些字段
    sync = {
        "rank_score": load.get("user_info", {}).get("rank_score"),
        "release_card_array": [x["card_id"] for x in load.get("card_list", [])],
    }
    for k, v in sync.items():
        if v is None:
            continue
        old = nd.get(k)
        nd[k] = v
        print(f"  {k}: {str(old)[:40]} -> {str(v)[:40]}")

    # top_directory_card_array 也同步
    if "top_directory_card_array" in nd:
        nd["top_directory_card_array"] = sync["release_card_array"][:10]

    new = msgpack.packb(note, use_bin_type=True)
    print(f"重编码: {len(items[NOTE_DECL])} -> {len(new)} B")

    items.pop(NOTE_DECL, None)
    items[len(new)] = new

    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["note/index"] = len(new)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print(f"path_declared note/index = {len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
