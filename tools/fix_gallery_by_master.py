"""按 master.mdb 重建图鉴相关数据 —— 严格遵循昨晚验证过的方案。

规则（用户明确要求）：
  1. chara_list 只能放"名下确实有事件数据"的角色
     → 有 gallery 事件的角色（master 里 135 个），无事件的 38 个角色一律排除
  2. event_data_array 的 data_id 必须是真实 story_id（master.single_mode_story_data）
  3. card_list 按 chara_id 过滤：card_id // 100 必须在 chara_list 里
  4. note/index 的 release_card_array 必须与 card_list 一致（名鉴读取它）
  5. cloth_list 用 master 全部 dress_data（含新实装 100946）
  6. 保留 character_story_data_list（剧情 7/7）、金币、钥匙

输出：load/index 与 note/index 同步更新
"""
from __future__ import annotations

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
    con = sqlite3.connect(MDB)
    cur = con.cursor()
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

    ev_by_chara = defaultdict(list)
    for sid, cid in gal_rows:
        if cid in impl_chara:
            ev_by_chara[cid].append(sid)
    valid_chara = set(ev_by_chara)

    print(f"master: chara={len(impl_chara)} card={len(real_card)} dress={len(real_dress)}")
    print(f"有 gallery 事件的角色: {len(valid_chara)}")
    print(f"无事件、将被排除的角色: {len(impl_chara - valid_chara)}")

    decl = json.loads(DECL.read_text(encoding="utf-8"))
    items = load_replay(REPLAY)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    # ============ load/index ============
    li_decl = decl.get("load/index")
    raw = items.get(li_decl)
    if raw is None:
        print(f"replay.bin 里没有 declared={li_decl}")
        return 1
    v = msgpack.unpackb(raw, raw=False, strict_map_key=False, unicode_errors="replace")
    d = v["data"]

    # 1) event_data_array —— master 全量（全解锁）
    event_data = []
    for cid in sorted(ev_by_chara):
        for sid in ev_by_chara[cid]:
            event_data.append({"chara_id": cid, "data_id": sid,
                               "create_time": now_str, "new_flag": 0})
    d["event_data_array"] = event_data
    print(f"\nevent_data_array: {len(event_data)} 条（全部真实 story_id）")

    # 2) chara_list —— 只保留有事件的角色
    old_chara = {c["chara_id"]: c for c in (d.get("chara_list") or [])
                 if isinstance(c, dict) and "chara_id" in c}
    new_chara = []
    created = 0
    for cid in sorted(valid_chara):
        if cid in old_chara:
            new_chara.append(old_chara[cid])
        else:
            dress = sorted(dress_by_chara.get(cid, []))
            new_chara.append({
                "chara_id": cid, "training_num": 0, "love_point": 0, "fan": 0,
                "max_grade": 1, "dress_id": dress[0] if dress else 1,
                "mini_dress_id": 2, "dress_color_id": 0,
                "mini_dress_color_id": 0, "create_time": now_str,
                "love_point_pool": 0,
            })
            created += 1
    old_n = len(d.get("chara_list") or [])
    d["chara_list"] = new_chara
    print(f"chara_list: {old_n} -> {len(new_chara)}（新建 {created}，排除无事件角色）")

    # 3) card_list —— 按 chara_id 过滤 + 只留真实 card
    old_card = d.get("card_list") or []
    new_card = []
    seen = set()
    for c in old_card:
        cid = None
        if isinstance(c, dict):
            cid = c.get("card_id") or c.get("id")
        elif isinstance(c, int):
            cid = c
        if cid is None or cid not in real_card or cid in seen:
            continue
        if cid // 100 not in valid_chara:
            continue
        if not isinstance(c, dict):
            c = {"card_id": cid, "rarity": 1, "talent_level": 1,
                 "create_time": now_str, "skill_data_array": []}
        elif "card_id" not in c:
            c = dict(c); c["card_id"] = cid
        new_card.append(c)
        seen.add(cid)
    d["card_list"] = new_card
    print(f"card_list: {len(old_card)} -> {len(new_card)}（按 chara 过滤 + 只留真实卡）")

    # 4) cloth_list —— 全部真实服装
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
    added = 0
    for did in sorted(real_dress - have):
        new_cloth.append({"cloth_id": did})
        added += 1
    d["cloth_list"] = new_cloth
    print(f"cloth_list: {len(old_cloth)} -> {len(new_cloth)}（补 {added} 件，含 100946）")

    # 5) load/index 的 release_card_array
    card_ids = {c["card_id"] for c in new_card}
    d["release_card_array"] = sorted(card_ids)
    print(f"load/index release_card_array: {len(d['release_card_array'])}")

    # 6) chara_profile_array 与 chara_list 对齐
    prof = d.get("chara_profile_array")
    if isinstance(prof, list):
        kept = [p for p in prof if isinstance(p, dict) and p.get("chara_id") in valid_chara]
        print(f"chara_profile_array: {len(prof)} -> {len(kept)}")
        d["chara_profile_array"] = kept

    # 7) 金币 / 钥匙（保留 7/7 剧情不动）
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
    print(f"coin_info = {COIN_TOTAL}/{COIN_TOTAL}，金币={COIN_TOTAL}，钥匙={KEY_TOTAL}")
    print(f"character_story_data_list 保留: {len(d.get('character_story_data_list') or [])} 条")

    hdrs = v.get("data_headers")
    if isinstance(hdrs, dict):
        hdrs["servertime"] = int(time.time())

    new_li = msgpack.packb(v, use_bin_type=True)

    # ============ note/index ============
    note_decl = decl.get("note/index")
    new_note = None
    if note_decl and note_decl in items:
        nv = msgpack.unpackb(items[note_decl], raw=False, strict_map_key=False,
                             unicode_errors="replace")
        nd_data = nv.get("data", {})
        old_rca = nd_data.get("release_card_array")
        if isinstance(old_rca, list):
            nd_data["release_card_array"] = sorted(card_ids)
            nh = nv.get("data_headers")
            if isinstance(nh, dict):
                nh["servertime"] = int(time.time())
            new_note = msgpack.packb(nv, use_bin_type=True)
            print(f"note/index release_card_array: {len(old_rca)} -> {len(card_ids)}")
    else:
        print("note/index 未找到，跳过")

    # ============ 写回 ============
    bak = REPLAY.with_name(f"replay.bin.bak_master_{time.strftime('%H%M%S')}")
    shutil.copy(REPLAY, bak)
    print(f"\n已备份 -> {bak.name}")

    items.pop(li_decl, None)
    items[len(new_li)] = new_li
    decl["load/index"] = len(new_li)
    print(f"load/index: {len(raw):,} -> {len(new_li):,} B")

    if new_note is not None:
        items.pop(note_decl, None)
        items[len(new_note)] = new_note
        decl["note/index"] = len(new_note)
        print(f"note/index: {len(new_note):,} B")

    save_replay(REPLAY, items)
    DECL.write_text(json.dumps(decl, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"replay.bin: {len(items)} 条")

    # ============ 最终核查 ============
    print("\n=== 最终核查 ===")
    cl = {c["chara_id"] for c in d["chara_list"]}
    ev_ch = {e["chara_id"] for e in d["event_data_array"]}
    ev_ids = {e["data_id"] for e in d["event_data_array"]}
    real_gal = {sid for sid, _ in gal_rows}
    print(f"  chara_list          {len(cl)}")
    print(f"  └ 全部有事件        {cl <= ev_ch}")
    print(f"  └ 无多余角色        {cl <= impl_chara}")
    print(f"  event_data_array    {len(ev_ids)} 个唯一 story_id")
    print(f"  └ 全部真实          {ev_ids <= real_gal}")
    print(f"  card_list           {len(card_ids)}  ⊂ release: {card_ids <= set(d['release_card_array'])}")
    print(f"  cloth_list          {len(d['cloth_list'])}  含 100946: {100946 in {c['cloth_id'] for c in d['cloth_list']}}")
    print(f"  note/index 已同步   {new_note is not None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
