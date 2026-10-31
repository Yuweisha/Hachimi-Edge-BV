"""补全 chara_profile_array：每个角色补到 6 条（data_id 1..6），与正常角色（1001）一致。"""
import json
import shutil
import struct
import sys

import msgpack

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
TARGET_N = 6


def main() -> int:
    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    decl0, v0 = None, None
    for decl, data in items.items():
        if decl < 1_000_000:
            continue
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
            if isinstance(v, dict) and "chara_profile_array" in v.get("data", {}):
                decl0, v0 = decl, v
        except Exception:
            pass
    if not decl0:
        print("找不到 load/index")
        return 1

    d = v0["data"]
    cp = d["chara_profile_array"]
    print(f"load/index declared={decl0}")
    print(f"chara_profile_array: {len(cp)} 条")

    # 按 chara_id 分组
    by_chara: dict[int, set[int]] = {}
    for e in cp:
        by_chara.setdefault(e["chara_id"], set()).add(e["data_id"])

    # 模板：取 data_id=1 的条目
    tpl = next((e for e in cp if e["data_id"] == 1), dict(cp[0]))
    tpl = dict(tpl)

    added = 0
    for cid, have in by_chara.items():
        for did in range(1, TARGET_N + 1):
            if did in have:
                continue
            e = dict(tpl)
            e["chara_id"] = cid
            e["data_id"] = did
            e["new_flag"] = 0
            cp.append(e)
            added += 1

    cp.sort(key=lambda x: (x["chara_id"], x["data_id"]))
    print(f"补了 {added} 条 -> {len(cp)} 条")
    print(f"覆盖 {len({e['chara_id'] for e in cp})} 个角色")

    shutil.copy(REPLAY, REPLAY.replace(".bin", ".bin.bak_profile"))
    new = msgpack.packb(v0, use_bin_type=True)
    print(f"重编码 {len(items[decl0])} -> {len(new)} B")

    items.pop(decl0)
    items[len(new)] = new
    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for dd, data in sorted(items.items()):
        out += struct.pack("<III", dd, dd, len(data)) + data
    open(REPLAY, "wb").write(out)
    print(f"replay.bin: {len(items)} 条, {len(out)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["load/index"] = len(new)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"path_declared load/index = {len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
