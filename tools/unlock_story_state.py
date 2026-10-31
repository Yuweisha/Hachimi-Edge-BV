"""解锁所有活动剧情：把 extra_story_data_list.story_event 的 state 全置 1。"""
import glob
import json
import os
import struct
import sys

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"


def patch(raw: bytes) -> bytes:
    v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    d = v["data"]
    ex = d.get("extra_story_data_list")
    if not isinstance(ex, dict):
        return raw
    changed = 0
    for k, arr in ex.items():
        if not isinstance(arr, list):
            continue
        for it in arr:
            if isinstance(it, dict) and "state" in it and it["state"] != 1:
                it["state"] = 1
                changed += 1
    print(f"  extra_story_data_list: {changed} 条 state -> 1")
    return msgpack.packb(v, use_bin_type=True)


def main() -> int:
    # 用最新的在线抓包（含真实进度）
    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if "load_index" in os.path.basename(f)]
    if not cands:
        print("找不到 load_index")
        return 1
    f = max(cands, key=os.path.getmtime)
    raw = open(f, "rb").read()
    print(f"源: {os.path.basename(f)} ({len(raw)} B)")

    new = patch(raw)
    print(f"重编码: {len(raw)} -> {len(new)} B")

    # 替换 replay.bin 里的 load/index
    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        data = b[off:off + dl]
        off += dl
        if 1_200_000 < decl < 1_300_000:
            try:
                vv = msgpack.unpackb(data, raw=False, strict_map_key=False)
                if isinstance(vv, dict) and "coin_info" in vv.get("data", {}):
                    continue
            except Exception:
                pass
        items[decl] = data
    items[len(new)] = new

    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["load/index"] = len(new)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print(f"path_declared load/index = {len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
