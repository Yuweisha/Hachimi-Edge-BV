"""生成抽卡变体：用变长字段制造不同的 declared。

手段：
- additional_piece_num 取不同量级（0/5/300/70000）→ uint8/uint16/uint32
- convert_piece_num 同理
- bonus_item_array 填充不同数量的元素
"""
from __future__ import annotations

import copy
import json
import random
import shutil
import sqlite3
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyderby_Jpn/master/master.mdb"
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
VARIANTS = 24


def load_items():
    b = REPLAY.read_bytes()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, d, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[d] = b[off:off + dl]
        off += dl
    return items


def find_template(items):
    for sz, data in items.items():
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        except Exception:
            continue
        d = v.get("data", {})
        if isinstance(d, dict) and "gacha_result_list" in d:
            return sz, v
    return None, None


def main() -> int:
    items = load_items()
    tpl_sz, tpl = find_template(items)
    if tpl is None:
        print("找不到模板")
        return 1
    print(f"模板 {tpl_sz} B")

    con = sqlite3.connect(MDB)
    cur = con.cursor()
    gid = tpl["data"].get("limit_item_info", {}).get("gacha_id", 30476)
    cur.execute("SELECT card_id, card_type, rarity, odds FROM gacha_available WHERE gacha_id=?", (gid,))
    pool = cur.fetchall()
    con.close()
    if not pool:
        print("卡池为空")
        return 1
    ids = [x[0] for x in pool]
    weights = [max(x[3], 1e-4) for x in pool]
    types = {x[0]: x[1] for x in pool}
    rar = {x[0]: x[2] for x in pool}
    print(f"卡池 {len(pool)} 张 (gacha_id={gid})")

    # 长度调节值（制造不同编码宽度）
    pad_choices = [0, 5, 200, 60000]

    results = []
    used_sizes = set(items)
    for i in range(VARIANTS):
        cid = random.choices(ids, weights=weights, k=1)[0]
        ct = types.get(cid, 1)
        pad = pad_choices[i % len(pad_choices)]
        extra = (i // len(pad_choices))  # 0..5，用于 bonus 填充

        v = copy.deepcopy(tpl)
        d = v["data"]
        d["gacha_result_list"] = [{
            "card_type": ct,
            "card_id": cid,
            "piece_id": cid if ct == 1 else 0,
            "common_item_category": 0,
            "common_item_id": 0,
            "convert_piece_num": pad,
            "convert_common_item_num": 0,
            "additional_piece_num": pad if ct == 1 else 0,
            "new_flag": 0,
            "win_prize": 0,
        }]
        rs = d.setdefault("reward_summary_info", {})
        if ct == 1:
            rs["add_piece_list"] = [{"piece_id": cid, "piece_num": max(pad, 1)}]
            rs["add_item_list"] = []
        else:
            rs["add_piece_list"] = []
            rs["add_item_list"] = [{"item_id": 115, "number": max(pad, 1)}]
        # bonus 填充（改变长度）
        d["bonus_item_array"] = [{"item_id": 115 + j, "number": 1} for j in range(extra)]

        data = msgpack.packb(v, use_bin_type=True)
        sz = len(data)
        if sz in used_sizes:
            print(f"  #{i+1} card={cid} 长度 {sz} 冲突，跳过")
            continue
        used_sizes.add(sz)
        items[sz] = data
        results.append((sz, cid, ct, rar.get(cid)))
        print(f"  #{i+1} declared={sz} card={cid} type={ct} rarity={rar.get(cid)} pad={pad} bonus={extra}")

    if not results:
        print("一个变体都没生成")
        return 1

    shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_gacha2"))
    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for d, data in sorted(items.items()):
        out += struct.pack("<III", d, d, len(data)) + data
    REPLAY.write_bytes(out)
    print(f"\nreplay.bin: {len(items)} 条, {len(out)} B（新增 {len(results)}）")

    vf = Path(r"C:/Users/Schwarz/uma_replay/gacha_variants.json")
    vf.write_text(json.dumps([x[0] for x in results], indent=2), encoding="utf-8")
    print(f"变体 declared 清单: {[x[0] for x in results]}")
    print(f"已写 {vf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
