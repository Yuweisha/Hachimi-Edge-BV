"""直接修改 load/index 里的金币和宝石，写入 replay.bin。

改这三处：
  data.coin_info.fcoin      → 100000000（宝石）
  data.coin_info.coin       → 100000000
  data.item_list[item_id=13].number → 100000000（金币）
  data.tp_info.current_tp / rp_info.current_rp 也拉满
"""
from __future__ import annotations

import json
import shutil
import struct
import sys

import msgpack

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
TARGET = 100_000_000


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_money")

    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    # 找 load/index（有 coin_info 的最大那条）
    best = None
    for decl, data in items.items():
        if not (1_200_000 < decl < 1_350_000):
            continue
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False)
            if isinstance(v, dict) and "coin_info" in v.get("data", {}):
                if best is None or decl > best[0]:
                    best = (decl, data, v)
        except Exception:
            pass
    if not best:
        print("找不到 load/index")
        return 1

    decl0, raw, v = best
    d = v["data"]
    print(f"load/index declared={decl0}")

    old_coin = dict(d.get("coin_info", {}))
    d["coin_info"]["fcoin"] = TARGET
    d["coin_info"]["coin"] = TARGET
    print(f"  coin_info: {old_coin} -> {d['coin_info']}")

    changed = 0
    for it in d.get("item_list", []):
        if isinstance(it, dict) and it.get("item_id") == 13:
            print(f"  item 13: {it.get('number')} -> {TARGET}")
            it["number"] = TARGET
            changed += 1
    print(f"  item 13 修改 {changed} 处")

    for k, sub in (("tp_info", "current_tp"), ("rp_info", "current_rp")):
        if k in d and sub in d[k]:
            print(f"  {k}.{sub}: {d[k][sub]} -> {d[k].get('max_' + sub.split('_')[1], TARGET)}")
            d[k][sub] = d[k].get("max_" + sub.split("_")[1], TARGET)

    new = msgpack.packb(v, use_bin_type=True)
    print(f"重编码: {len(raw)} -> {len(new)} B")

    items.pop(decl0, None)
    items[len(new)] = new

    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for dd, data in sorted(items.items()):
        o += struct.pack("<III", dd, dd, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")

    m = json.load(open(DECL, encoding="utf-8"))
    m["load/index"] = len(new)
    json.dump(m, open(DECL, "w", encoding="utf-8"), indent=2)
    print(f"path_declared load/index = {len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
