"""按稀有度权重生成抽卡变体。

权重（角色卡）：
  3★ 3.00%  2★ 18.00%  1★ 79.00%
同稀有度内所有卡等概率。
"""
from __future__ import annotations

import copy
import json
import random
import shutil
import sqlite3
import struct
from collections import defaultdict
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"

VARIANTS = 40
RARITY_W = {3: 0.03, 2: 0.18, 1: 0.79}


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


def pick(pools: dict[int, list[int]]) -> tuple[int, int]:
    """按权重选稀有度，再等概率选卡。返回 (card_id, rarity)。"""
    rarities = [r for r in pools if r in RARITY_W]
    weights = [RARITY_W[r] for r in rarities]
    r = random.choices(rarities, weights=weights, k=1)[0]
    cid = random.choice(pools[r])
    return cid, r


def main() -> int:
    items = load_items()
    tpl_sz, tpl = find_template(items)
    if tpl is None:
        print("找不到模板")
        return 1
    print(f"模板 {tpl_sz} B")

    gid = tpl["data"].get("limit_item_info", {}).get("gacha_id", 30476)
    con = sqlite3.connect(MDB)
    cur = con.cursor()
    cur.execute("SELECT card_id, rarity FROM gacha_available WHERE gacha_id=? AND card_type=1", (gid,))
    rows = cur.fetchall()
    con.close()

    pools = defaultdict(list)
    for cid, rar in rows:
        pools[rar].append(cid)
    print(f"gacha_id={gid} 角色卡池:")
    for r in sorted(pools, reverse=True):
        print(f"  {r}★: {len(pools[r])} 张  权重 {RARITY_W.get(r, 0)*100:.2f}%")
    print(f"  合计 {sum(len(v) for v in pools.values())} 张")

    if not pools:
        print("卡池为空")
        return 1

    pad_choices = [0, 5, 200, 60000]
    used = set(items)
    results = []
    stats = defaultdict(int)

    for i in range(VARIANTS):
        cid, rar = pick(pools)
        stats[rar] += 1
        pad = pad_choices[i % len(pad_choices)]
        extra = i // len(pad_choices)

        v = copy.deepcopy(tpl)
        d = v["data"]
        d["gacha_result_list"] = [{
            "card_type": 1,
            "card_id": cid,
            "piece_id": cid,
            "common_item_category": 0,
            "common_item_id": 0,
            "convert_piece_num": pad,
            "convert_common_item_num": 0,
            "additional_piece_num": pad,
            "new_flag": 0,
            "win_prize": 0,
        }]
        rs = d.setdefault("reward_summary_info", {})
        rs["add_piece_list"] = [{"piece_id": cid, "piece_num": max(pad, 1)}]
        rs["add_item_list"] = []
        d["bonus_item_array"] = [{"item_id": 115 + j, "number": 1} for j in range(extra)]

        data = msgpack.packb(v, use_bin_type=True)
        sz = len(data)
        if sz in used:
            continue
        used.add(sz)
        items[sz] = data
        results.append((sz, cid, rar))

    if not results:
        print("没有新变体（长度全冲突）")
        return 1

    print(f"\n生成 {len(results)} 个变体，稀有度分布: {dict(stats)}")
    for sz, cid, rar in results[:8]:
        print(f"  declared={sz} card={cid} {rar}★")

    shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_gacha3"))
    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for d, data in sorted(items.items()):
        out += struct.pack("<III", d, d, len(data)) + data
    REPLAY.write_bytes(out)
    print(f"\nreplay.bin: {len(items)} 条, {len(out)} B")

    vf = Path(r"C:/Users/Schwarz/uma_replay/gacha_variants.json")
    vf.write_text(json.dumps([x[0] for x in results], indent=2), encoding="utf-8")
    print(f"变体 {len(results)} 个已写入 {vf.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
