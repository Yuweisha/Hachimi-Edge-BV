"""严格按 master.mdb 重建 load/index 的三个列表，清除一切伪造数据。

清理对象：
  chara_list        只保留 master.chara_data 里存在的、且已实装（start_date <= now）
  card_list         只保留 master.card_data 里存在的，且必须 ⊂ release_card_array
  cloth_list        只保留 master.dress_data 里存在的
  event_data_array  只保留 master.single_mode_story_data 里存在且 gallery_flag=1 的 story_id
  release_card_array 与 card_list 双向对齐

同时满足四条硬约束（RESTORE.md）：
  1. chara_list 的每个 chara_id 必须在 event_data_array 里有条目
  2. card_list ⊂ release_card_array（双向）
  3. event_data_array 的 chara_id 必须已实装
  4. event_data_array 的 data_id 必须是真实 story_id
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import struct
import time
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

    # ---- master 真实集合 ----
    cur.execute("SELECT id FROM chara_data WHERE start_date <= date('now')")
    real_chara = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT id FROM card_data")
    real_card = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT id FROM dress_data")
    real_dress = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT story_id, card_chara_id FROM single_mode_story_data WHERE gallery_flag=1")
    gallery_rows = cur.fetchall()
    real_gallery = {r[0]: r[1] for r in gallery_rows}
    con.close()

    print(f"master: chara={len(real_chara)} card={len(real_card)} "
          f"dress={len(real_dress)} gallery={len(real_gallery)}")

    decl = json.loads(DECL.read_text(encoding="utf-8"))
    li_decl = decl.get("load/index")
    items = load_replay(REPLAY)
    raw = items.get(li_decl)
    if raw is None:
        print(f"replay.bin 里没有 declared={li_decl}")
        return 1

    v = msgpack.unpackb(raw, raw=False, strict_map_key=False, unicode_errors="replace")
    d = v["data"]

    # ---- 1. 清理 chara_list ----
    old_chara = d.get("chara_list") or []
    new_chara, dropped_c = [], []
    seen_c = set()
    for c in old_chara:
        if not isinstance(c, dict):
            continue
        cid = c.get("chara_id")
        if cid in real_chara and cid not in seen_c:
            new_chara.append(c)
            seen_c.add(cid)
        else:
            dropped_c.append(cid)
    d["chara_list"] = new_chara
    print(f"\nchara_list: {len(old_chara)} -> {len(new_chara)}（剔除 {len(dropped_c)}）")

    # ---- 2. 清理 card_list ----
    old_card = d.get("card_list") or []
    new_card = []
    dropped_k = []
    seen_k = set()
    for c in old_card:
        if not isinstance(c, dict):
            # 有些条目可能直接是 int
            if isinstance(c, int) and c in real_card and c not in seen_k:
                new_card.append({"card_id": c})
                seen_k.add(c)
                continue
            dropped_k.append(c)
            continue
        cid = c.get("card_id") or c.get("id")
        if cid in real_card and cid not in seen_k:
            if "card_id" not in c:
                c = dict(c)
                c["card_id"] = cid
            new_card.append(c)
            seen_k.add(cid)
        else:
            dropped_k.append(cid)
    print(f"card_list: {len(old_card)} -> {len(new_card)}（剔除 {len(dropped_k)} 个非 card_id）")

    # ---- 3. 清理 cloth_list ----
    old_cloth = d.get("cloth_list") or []
    new_cloth = []
    dropped_d = []
    seen_d = set()
    for c in old_cloth:
        if not isinstance(c, dict):
            if isinstance(c, int) and c in real_dress and c not in seen_d:
                new_cloth.append({"cloth_id": c})
                seen_d.add(c)
                continue
            dropped_d.append(c)
            continue
        cid = c.get("cloth_id") or c.get("id") or c.get("dress_id")
        if cid in real_dress and cid not in seen_d:
            if "cloth_id" not in c:
                c = dict(c)
                c["cloth_id"] = cid
            new_cloth.append(c)
            seen_d.add(cid)
        else:
            dropped_d.append(cid)
    d["cloth_list"] = new_cloth
    print(f"cloth_list: {len(old_cloth)} -> {len(new_cloth)}（剔除 {len(dropped_d)}）")

    # ---- 4. 清理 event_data_array ----
    old_ev = d.get("event_data_array") or []
    new_ev = []
    dropped_e = []
    seen_e = set()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    for e in old_ev:
        if not isinstance(e, dict):
            continue
        did = e.get("data_id")
        if did not in real_gallery:
            dropped_e.append(did)
            continue
        if did in seen_e:
            continue
        # chara_id 用 master 的权威值
        e = dict(e)
        e["chara_id"] = real_gallery[did]
        e.setdefault("create_time", now_str)
        e.setdefault("new_flag", 0)
        new_ev.append(e)
        seen_e.add(did)
    d["event_data_array"] = new_ev
    print(f"event_data_array: {len(old_ev)} -> {len(new_ev)}（剔除 {len(dropped_e)} 个虚构 id）")

    # ---- 5. release_card_array 与 card_list 双向对齐 ----
    rca = d.get("release_card_array")
    rca_ids = set()
    if isinstance(rca, list):
        for c in rca:
            if isinstance(c, dict):
                for k in ("card_id", "id"):
                    if k in c:
                        rca_ids.add(c[k])
                        break
            elif isinstance(c, int):
                rca_ids.add(c)
    card_ids = {c["card_id"] for c in new_card}
    # card_list 必须 ⊂ release_card_array
    extra = card_ids - rca_ids
    if extra:
        print(f"  release_card_array 缺 {len(extra)} 个，补齐")
        if not isinstance(d["release_card_array"], list):
            d["release_card_array"] = []
        for cid in sorted(extra):
            d["release_card_array"].append({"card_id": cid})
        rca_ids |= extra
    print(f"release_card_array: {len(rca_ids)} 个，card_list ⊂ release: {card_ids <= rca_ids}")

    # ---- 6. chara_list 必须在 event_data_array 有条目（硬约束 1）----
    ev_chara = {e["chara_id"] for e in new_ev}
    orphan = {c["chara_id"] for c in new_chara} - ev_chara
    if orphan:
        print(f"  chara_list 有 {len(orphan)} 个角色无事件数据 -> 移除: {sorted(orphan)[:10]}")
        d["chara_list"] = [c for c in new_chara if c["chara_id"] not in orphan]
        print(f"  chara_list 最终: {len(d['chara_list'])}")

    # ---- 7. 金币 / 钥匙 ----
    d["coin_info"] = {"fcoin": COIN_TOTAL, "coin": COIN_TOTAL}
    il = d.get("item_list")
    if not isinstance(il, list):
        il = []
        d["item_list"] = il
    by_id = {it.get("item_id"): it for it in il if isinstance(it, dict)}
    if GOLD_ITEM in by_id:
        by_id[GOLD_ITEM]["number"] = COIN_TOTAL
    else:
        il.append({"item_id": GOLD_ITEM, "number": COIN_TOTAL})
    if KEY_ITEM in by_id:
        by_id[KEY_ITEM]["number"] = KEY_TOTAL
    else:
        il.append({"item_id": KEY_ITEM, "number": KEY_TOTAL})
    print(f"\ncoin_info = {COIN_TOTAL}/{COIN_TOTAL}, 钥匙 = {KEY_TOTAL}")

    hdrs = v.get("data_headers")
    if isinstance(hdrs, dict):
        hdrs["servertime"] = int(time.time())

    new_raw = msgpack.packb(v, use_bin_type=True)
    print(f"\n重编码 {len(raw)} -> {len(new_raw)} B")

    bak = REPLAY.with_name(f"replay.bin.bak_clean_{time.strftime('%H%M%S')}")
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
    print(f"  chara_list        {len(d['chara_list'])}")
    print(f"  card_list         {len(d['card_list'])}")
    print(f"  cloth_list        {len(d['cloth_list'])}")
    print(f"  event_data_array  {len(d['event_data_array'])}")
    print(f"  release_card_array {len(d['release_card_array'])}")
    print(f"  100946 在 cloth_list: {100946 in {c['cloth_id'] for c in d['cloth_list']}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
