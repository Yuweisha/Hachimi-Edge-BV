"""清掉所有 new 标记：遍历 load_index 里所有含 new_flag 的字段，全置 0。

保留：剧情解锁（extra_story_data_list.story_event[].state = 1）
     角色解锁（chara_list / card_list / cloth_list 的补全）
"""
import glob
import json
import os
import shutil
import struct
import sys

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"


def walk_clear(o, path=""):
    """递归把所有 new_flag / is_new 置 0，返回改动数。"""
    n = 0
    if isinstance(o, dict):
        for k in list(o.keys()):
            if k in ("new_flag", "is_new", "is_read") and isinstance(o[k], int):
                if o[k] != 0:
                    o[k] = 0
                    n += 1
            else:
                n += walk_clear(o[k], f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            n += walk_clear(v, f"{path}[{i}]")
    return n


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_new")

    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    target_decl = 0
    target_data = None
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        data = b[off:off + dl]
        off += dl
        items[decl] = data
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False)
            dd = v.get("data") if isinstance(v, dict) else None
            if isinstance(dd, dict) and "coin_info" in dd and decl > target_decl:
                target_decl, target_data = decl, data
        except Exception:
            pass
    print(f"load/index declared={target_decl}")

    v = msgpack.unpackb(target_data, raw=False, strict_map_key=False)
    d = v["data"]

    # 先统计各字段的 new 标记数
    before = {}
    for k, val in d.items():
        c = walk_clear(val, k)
        if c:
            before[k] = c
            # walk_clear 已经改了；这里要重新构造一次以确认
    print("清理的 new 标记:", before if before else "（无）")

    # 重新做一次（因为上面可能已改）
    v2 = msgpack.unpackb(target_data, raw=False, strict_map_key=False)
    d2 = v2["data"]
    total = 0
    for k in d2:
        total += walk_clear(d2[k], k)
    print(f"总计清掉 {total} 个 new 标记")

    # 额外：把 state=1 但可能带「未读」语义的也检查
    new = msgpack.packb(v2, use_bin_type=True)
    print(f"重编码: {len(target_data)} -> {len(new)} B")

    items.pop(target_decl, None)
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
