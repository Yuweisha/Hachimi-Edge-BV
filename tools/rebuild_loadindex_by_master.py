"""按 master.mdb 严格重建 load/index 的所有列表 —— 零伪造数据。

规则：
  chara_list          = master 里**有 gallery 事件**的角色（135 个），字段完整
  event_data_array    = master 全部 gallery_flag=1 事件（13555 条，0.88 MB）
  card_list           = master.card_data 里真实存在的卡
  cloth_list          = master.dress_data 全部（521，含新实装的 100946）
  release_card_array  = 与 card_list 双向对齐
  chara_profile_array = 与 chara_list 对齐

四条硬约束全部满足：
  1. chara_list 的 chara_id 一定有 event_data_array 条目（因为都从 gallery 事件反推）
  2. card_list ⊂ release_card_array
  3. event_data_array 的 chara_id 都已实装
  4. event_data_array 的 data_id 都是真实 story_id

用法：
  python rebuild_loadindex_by_master.py [--max-events-per-chara N]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import struct
import time
from collections import defaultdict
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
MDB = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb"

COIN_TOTAL = 100_000_000
KEY_ITEM = 190
KEY_TOTAL = 9999
GOLD_ITEM = 59


def load_replay(path: Path) -> dict[int, bytes]:
    b = path.read_bytes()
    assert b[:4] == b"RPLY"
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        _a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl
    return items


def save_replay(path: Path, items: dict[int, bytes]) -> None:
    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        out += struct.pack("<III", decl, decl, len(data)) + data
    path.write_bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-events-per-chara", type=int, default=0,
                    help="每个角色最多保留多少条事件（0=全部）")
    a = ap.parse_args()

    con = sqlite3.connect(MDB)
    cur = con.cursor()

    # master 真实数据
    cur.execute("SELECT id FROM chara_data WHERE start_date <= date('now')")
    impl_chara = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT id FROM card_data")
    real_card = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT id, chara_id FROM dress_data")
    dress_rows = cur.fetchall()
    real_dress = {r[0] for r in dress_rows}
    dress_by_chara = defaultdict(list)
    for did, cid in dress_rows:
        dress_by_chara[cid].append(did)
    cur.execute("SELECT story_id, card_chara_id FROM single_mode_story_data "
                "WHERE gallery_flag=1 ORDER BY card_chara_id, story_id")
    gal_rows = cur.fetchall()
    con.close()

    print(f"master: chara={len(impl_chara)} card={len(real_card)} "
          f"dress={len(real_dress)} gallery_events={len(gal_rows)}")

    # 按角色分组事件
    ev_by_chara = defaultdict(list)
    for sid, cid in gal_rows:
        if cid in impl_chara:
            ev_by_chara[cid].append(sid)

    print(f"有 gallery 事件的角色: {len(ev_by_chara)}")
    print(f"无 gallery 事件的角色: {len(impl_chara) - len(ev_by_chara)}（不放进 chara_list）")

    # ---- 构造 event_data_array ----
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    event_data = []
    for cid in sorted(ev_by_chara):
        ids = ev_by_chara[cid]
        if a.max_events_per_chara:
            ids = ids[:a.max_events_per_chara]
        for sid in ids:
            event_data.append({
                "chara_id": cid,
                "data_id": sid,
                "create_time": now_str,
                "new_flag": 0,
            })
    print(f"event_data_array: {len(event_data)} 条")

    # ---- 读取现有 load/index ----
    decl = json.loads(DECL.read_text(encoding="utf-8"))
    li_decl = decl.get("load/index")
    items = load_replay(REPLAY)
    raw = items.get(li_decl)
    if raw is None:
        print(f"replay.bin 里没有 declared={li_decl}")
        return 1
    v = msgpack.unpackb(raw, raw=False, strict_map_key=False, unicode_errors="replace")
    d = v["data"]

    # ---- chara_list ----
    # 只放"至少有一个 gallery 事件"的角色；完全没有事件数据的角色不能加
    # （图鉴会读取事件表，无事件的角色会软死）
    old_chara = {c["chara_id"]: c for c in (d.get("chara_list") or [])
                 if isinstance(c, dict) and "chara_id" in c}
    new_chara = []
    created = 0
    for cid in sorted(ev_by_chara):
        if cid in old_chara:
            new_chara.append(old_chara[cid])
        else:
            # 从 master 造一个合法条目（用该角色第一件服装）
            dress = sorted(dress_by_chara.get(cid, []))
            new_chara.append({
                "chara_id": cid,
                "training_num": 0,
                "love_point": 0,
                "fan": 0,
                "max_grade": 1,
                "dress_id": dress[0] if dress else 1,
                "mini_dress_id": 2,
                "dress_color_id": 0,
                "mini_dress_color_id": 0,
                "create_time": now_str,
                "love_point_pool": 0,
            })
            created += 1
    d["chara_list"] = new_chara
    print(f"chara_list: {len(old_chara)} -> {len(new_chara)}"
          f"（新建 {created} 条；无事件的 {len(impl_chara) - len(ev_by_chara)} 个角色已排除）")

    # ---- card_list（只留真实 card）----
    old_card = d.get("card_list") or []
    new_card = []
    seen = set()
    dropped = 0
    for c in old_card:
        cid = None
        if isinstance(c, dict):
            cid = c.get("card_id") or c.get("id")
        elif isinstance(c, int):
            cid = c
        if cid in real_card and cid not in seen:
            if not isinstance(c, dict):
                c = {"card_id": cid, "rarity": 1, "talent_level": 1,
                     "create_time": now_str, "skill_data_array": []}
            elif "card_id" not in c:
                c = dict(c); c["card_id"] = cid
            new_card.append(c)
            seen.add(cid)
        else:
            dropped += 1
    d["card_list"] = new_card
    print(f"card_list: {len(old_card)} -> {len(new_card)}（剔除 {dropped}）")

    # ---- cloth_list（全部真实服装）----
    old_cloth = d.get("cloth_list") or []
    have = set()
    new_cloth = []
    for c in old_cloth:
        cid = None
        if isinstance(c, dict):
            cid = c.get("cloth_id") or c.get("id") or c.get("dress_id")
        elif isinstance(c, int):
            cid = c
        if cid in real_dress and cid not in have:
            if not isinstance(c, dict):
                c = {"cloth_id": cid}
            elif "cloth_id" not in c:
                c = dict(c); c["cloth_id"] = cid
            new_cloth.append(c)
            have.add(cid)
    for did in sorted(real_dress - have):
        new_cloth.append({"cloth_id": did})
    d["cloth_list"] = new_cloth
    print(f"cloth_list: {len(old_cloth)} -> {len(new_cloth)}（含新增 {len(real_dress - have)} 件）")

    # ---- release_card_array ----
    card_ids = {c["card_id"] for c in new_card}
    rca = d.get("release_card_array")
    rca_ids = set()
    if isinstance(rca, list):
        for c in rca:
            if isinstance(c, dict):
                for k in ("card_id", "id"):
                    if k in c:
                        rca_ids.add(c[k]); break
            elif isinstance(c, int):
                rca_ids.add(c)
    # 双向：只留真实 card，且覆盖所有 card_list
    final_rca = sorted((rca_ids | card_ids) & real_card)
    d["release_card_array"] = final_rca
    print(f"release_card_array: {len(rca_ids)} -> {len(final_rca)}，"
          f"card_list ⊂ release: {card_ids <= set(final_rca)}")

    # ---- event_data_array ----
    d["event_data_array"] = event_data

    # ---- chara_profile_array 与 chara_list 对齐 ----
    prof = d.get("chara_profile_array")
    if isinstance(prof, list):
        prof_ids = {p.get("chara_id") for p in prof if isinstance(p, dict)}
        chara_ids = {c["chara_id"] for c in new_chara}
        d["chara_profile_array"] = [p for p in prof
                                    if isinstance(p, dict) and p.get("chara_id") in chara_ids]
        print(f"chara_profile_array: {len(prof)} -> {len(d['chara_profile_array'])}")

    # ---- 金币 / 钥匙 ----
    d["coin_info"] = {"fcoin": COIN_TOTAL, "coin": COIN_TOTAL}
    il = d.get("item_list")
    if not isinstance(il, list):
        il = []
        d["item_list"] = il
    by_id = {it.get("item_id"): it for it in il if isinstance(it, dict)}
    for iid, num in ((GOLD_ITEM, COIN_TOTAL), (KEY_ITEM, KEY_TOTAL)):
        if iid in by_id:
            by_id[iid]["number"] = num
        else:
            il.append({"item_id": iid, "number": num})
    print(f"\ncoin_info = {COIN_TOTAL}/{COIN_TOTAL}，金币={COIN_TOTAL}，钥匙={KEY_TOTAL}")

    hdrs = v.get("data_headers")
    if isinstance(hdrs, dict):
        hdrs["servertime"] = int(time.time())

    new_raw = msgpack.packb(v, use_bin_type=True)
    print(f"\n重编码 {len(raw):,} -> {len(new_raw):,} B")

    bak = REPLAY.with_name(f"replay.bin.bak_master_{time.strftime('%H%M%S')}")
    shutil.copy(REPLAY, bak)
    print(f"已备份 -> {bak.name}")

    items.pop(li_decl, None)
    items[len(new_raw)] = new_raw
    save_replay(REPLAY, items)

    decl["load/index"] = len(new_raw)
    DECL.write_text(json.dumps(decl, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"replay.bin: {len(items)} 条")
    print(f"path_declared load/index = {len(new_raw)}")

    # ---- 最终核查 ----
    print("\n=== 最终核查 ===")
    cl = {c["chara_id"] for c in d["chara_list"]}
    ev_ch = {e["chara_id"] for e in d["event_data_array"]}
    print(f"  chara_list          {len(cl)}  全部有事件: {cl <= ev_ch}")
    print(f"  event_data_array    {len(d['event_data_array'])}")
    print(f"  card_list           {len(d['card_list'])}  ⊂ release: {card_ids <= set(final_rca)}")
    print(f"  cloth_list          {len(d['cloth_list'])}  含 100946: {100946 in {c['cloth_id'] for c in d['cloth_list']}}")
    print(f"  release_card_array  {len(final_rca)}")
    print(f"  所有 data_id 真实: {set(e['data_id'] for e in d['event_data_array']) <= {r[0] for r in gal_rows}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
