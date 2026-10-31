"""解锁全部育成赛马娘：补全 chara_list / card_list / cloth_list。"""
import glob
import json
import os
import shutil
import sqlite3
import struct
import sys

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_chara")

    c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
    all_chara = [r[0] for r in c.execute("SELECT id FROM chara_data ORDER BY id")]
    all_dress = [(r[0], r[1], r[2]) for r in
                 c.execute("SELECT id, chara_id, general_purpose FROM dress_data ORDER BY id")]
    print(f"master: chara={len(all_chara)}, dress={len(all_dress)}")

    # 取当前 load/index（replay.bin 里最大的那条）
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

    # --- chara_list ---
    have_chara = {x["chara_id"] for x in d.get("chara_list", [])}
    tmpl_chara = d["chara_list"][0]
    new_chara = list(d.get("chara_list", []))
    added_c = 0
    for cid in all_chara:
        if cid in have_chara:
            continue
        # 找该角色第一个 dress
        dress = next((dr for dr in all_dress if dr[1] == cid), None)
        item = dict(tmpl_chara)
        item.update({
            "chara_id": cid,
            "training_num": 0,
            "love_point": 0,
            "fan": 0,
            "max_grade": 1,
            "dress_id": dress[0] if dress else 0,
            "mini_dress_id": 2,
            "dress_color_id": 0,
            "mini_dress_color_id": 0,
            "create_time": "2024-01-01 00:00:00",
            "love_point_pool": 0,
        })
        new_chara.append(item)
        added_c += 1
    d["chara_list"] = new_chara
    print(f"chara_list: +{added_c} -> {len(new_chara)}")

    # --- card_list ---
    # card_id = dress_id（100101 这种），用 chara 的 dress
    have_card = {x["card_id"] for x in d.get("card_list", [])}
    tmpl_card = d["card_list"][0]
    new_card = list(d.get("card_list", []))
    added_k = 0
    for dress_id, chara_id, general in all_dress:
        if not general:
            continue  # general_purpose=0 是通用服装，不是卡
        if dress_id in have_card:
            continue
        item = dict(tmpl_card)
        item.update({
            "card_id": dress_id,
            "rarity": 3,
            "talent_level": 1,
            "create_time": "2024-01-01 00:00:00",
            "skill_data_array": [],
        })
        new_card.append(item)
        added_k += 1
    d["card_list"] = new_card
    print(f"card_list: +{added_k} -> {len(new_card)}")

    # --- cloth_list ---
    have_cloth = {x["cloth_id"] for x in d.get("cloth_list", [])}
    new_cloth = list(d.get("cloth_list", []))
    added_l = 0
    for dress_id, _, _ in all_dress:
        if dress_id not in have_cloth:
            new_cloth.append({"cloth_id": dress_id})
            added_l += 1
    d["cloth_list"] = new_cloth
    print(f"cloth_list: +{added_l} -> {len(new_cloth)}")

    new = msgpack.packb(v, use_bin_type=True)
    print(f"重编码: {len(target_data)} -> {len(new)} B")

    # 替换
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
