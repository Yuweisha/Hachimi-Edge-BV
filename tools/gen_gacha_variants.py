"""批量生成抽卡结果变体，写入 replay.bin（每个变体有独立的 declared）。

做法：
1. 以 980 B 的真实响应为模板
2. 从 master.gacha_available 按 odds 抽卡
3. 改写 gacha_result_list / reward_summary_info / coin_info 等字段
4. 每份结果长度不同 → 插件按 declared 查得到
"""
from __future__ import annotations

import json
import random
import sqlite3
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyderby_Jpn/master/master.mdb"
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"

VARIANTS = 20   # 生成 20 份不同结果


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


def find_template(items) -> tuple[int, dict] | tuple[None, None]:
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
        print("找不到 gacha/exec 模板")
        return 1
    print(f"模板: {tpl_sz} B")
    print("模板结构:", list(tpl["data"].keys()))

    # master 卡池
    con = sqlite3.connect(MDB)
    cur = con.cursor()
    print("\n=== 可用卡池 ===")
    cur.execute("""
        SELECT gacha_id, card_type, COUNT(*) as n
        FROM gacha_available GROUP BY gacha_id, card_type
        ORDER BY n DESC LIMIT 8
    """)
    for r in cur.fetchall():
        print(f"  gacha_id={r[0]} card_type={r[1]} {r[2]} 张")

    # 用模板里的 gacha_id
    gid = tpl["data"].get("limit_item_info", {}).get("gacha_id", 30476)
    print(f"\n用 gacha_id={gid} 抽卡")

    cur.execute("""
        SELECT card_id, card_type, rarity, odds FROM gacha_available
        WHERE gacha_id = ? ORDER BY odds DESC
    """, (gid,))
    pool = cur.fetchall()
    con.close()
    if not pool:
        print(f"gacha_id={gid} 没有 card pool")
        return 1
    print(f"卡池 {len(pool)} 张，odds 合计 {sum(x[3] for x in pool)}")

    # 加权抽样
    ids = [x[0] for x in pool]
    weights = [max(x[3], 0.0001) for x in pool]
    types = {x[0]: x[1] for x in pool}
    rarities = {x[0]: x[2] for x in pool}

    import copy
    results = []
    for i in range(VARIANTS):
        cid = random.choices(ids, weights=weights, k=1)[0]
        v = copy.deepcopy(tpl)
        d = v["data"]
        ct = types.get(cid, 1)
        d["gacha_result_list"] = [{
            "card_type": ct,
            "card_id": cid,
            "piece_id": cid if ct == 1 else 0,
            "common_item_category": 0,
            "common_item_id": 0,
            "convert_piece_num": 0,
            "convert_common_item_num": 0,
            "additional_piece_num": 5 if ct == 1 else 0,
            "new_flag": random.randint(0, 1),
            "win_prize": 0,
        }]
        rs = d.get("reward_summary_info", {})
        rs["add_piece_list"] = [{"piece_id": cid, "piece_num": 5}] if ct == 1 else []
        rs["add_card_list"] = [] if ct == 1 else [{
            "card_id": cid, "exp": 0, "limit_break_count": 0,
            "favorite_flag": 0, "stock": 0,
        }]
        d["item_list"] = []
        results.append((cid, ct, rarities.get(cid), v))
        print(f"  #{i+1}: card_id={cid} type={ct} rarity={rarities.get(cid)}")

    # 编码并入库
    import shutil
    shutil.copy(REPLAY, REPLAY.with_name("replay.bin.bak_gacha"))
    added = []
    for cid, ct, rar, v in results:
        data = msgpack.packb(v, use_bin_type=True)
        sz = len(data)
        if sz in items and items[sz] != data:
            # 长度冲突，跳过（可能性低，因为内容不同长度通常不同）
            print(f"  跳过 card {cid}：长度 {sz} 已被占用")
            continue
        items[sz] = data
        added.append((sz, cid))

    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for d, data in sorted(items.items()):
        out += struct.pack("<III", d, d, len(data)) + data
    REPLAY.write_bytes(out)
    print(f"\nreplay.bin: {len(items)} 条, {len(out)} B")
    print(f"新增抽卡变体 {len(added)} 个，declared = {[x[0] for x in added[:10]]}...")

    # 记录变体列表给服务器用
    var_file = Path(r"C:/Users/Schwarz/uma_replay/gacha_variants.json")
    var_file.write_text(json.dumps([x[0] for x in added], indent=2), encoding="utf-8")
    print(f"变体清单已写: {var_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
