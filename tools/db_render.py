"""从数据库渲染各接口响应。

设计：**模板法** —— 用录制数据的骨架兜底，只替换能由数据库推导的字段。
这样即使漏改某个字段，游戏也不会因为缺字段崩溃。

支持的接口：
  load/index             chara_list / card_list / cloth_list / item_list /
                         coin_info / event_data_array / character_story_data_list /
                         chara_profile_array
  note/index             release_card_array
  note/use_gallery_key   按请求的 story_id_array 解锁 + 扣钥匙
  note/save_chara_data   换装（改 owned_chara.dress_id）
  event_id_chara_id      按 story_id 生成剧情内容
  gallery/play_event     同上
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

VIEWER_ID = 601653962

import msgpack

BASE = Path(r"C:/Users/Schwarz/uma_replay")
DB_PATH = BASE / "offline.db"
MDB = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb"

_master_cache: dict = {}


def db() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH), timeout=5)


def master() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)


def now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ---------- 基础读取 ----------

def get_state(key: str, default=None):
    with db() as con:
        cur = con.execute("SELECT value FROM user_state WHERE key=?", (key,))
        r = cur.fetchone()
    return r[0] if r else default


def set_state(key: str, value) -> None:
    with db() as con:
        con.execute("INSERT OR REPLACE INTO user_state(key,value) VALUES (?,?)",
                    (key, str(value)))
        con.commit()


def all_chara() -> list[dict]:
    """角色列表。training_num 按数据库原值（0 不影响图鉴解锁）。"""
    with db() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM owned_chara ORDER BY chara_id").fetchall()
    out = []
    for r in rows:
        out.append({
            "chara_id": r["chara_id"],
            "training_num": r["training_num"] or 0,
            "love_point": r["love_point"],
            "fan": r["fan"],
            "max_grade": r["max_grade"],
            "dress_id": r["dress_id"],
            "mini_dress_id": r["mini_dress_id"],
            "dress_color_id": r["dress_color_id"],
            "mini_dress_color_id": r["mini_dress_color_id"],
            "create_time": r["create_time"],
            "love_point_pool": r["love_point_pool"],
        })
    return out


def all_card() -> list[dict]:
    with db() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM owned_card ORDER BY card_id").fetchall()
    out = []
    for r in rows:
        try:
            sk = msgpack.unpackb(r["skill_data"], raw=False, strict_map_key=False,
                                 unicode_errors="replace") if r["skill_data"] else []
        except Exception:
            sk = []
        # 客户端要求 skill_data_array 是数组；X'80' 会解出 {}，必须归一化
        if not isinstance(sk, list):
            sk = []
        out.append({
            "card_id": r["card_id"],
            "rarity": r["rarity"],
            "talent_level": r["talent_level"],
            "create_time": r["create_time"],
            "skill_data_array": sk,
        })
    return out


def all_cloth() -> list[dict]:
    with db() as con:
        rows = con.execute("SELECT cloth_id FROM owned_cloth ORDER BY cloth_id").fetchall()
    return [{"cloth_id": r[0]} for r in rows]


def all_events() -> list[dict]:
    with db() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT story_id, chara_id, unlocked_at, new_flag "
            "FROM unlocked_event ORDER BY chara_id, story_id").fetchall()
    return [{"chara_id": r["chara_id"], "data_id": r["story_id"],
             "create_time": r["unlocked_at"], "new_flag": r["new_flag"]}
            for r in rows]


def all_story_state() -> list[dict]:
    with db() as con:
        rows = con.execute(
            "SELECT episode_id, state FROM story_state ORDER BY episode_id").fetchall()
    return [{"episode_id": r[0], "state": r[1]} for r in rows]


# ---------- 卡的默认服装映射 ----------

def all_card_dress() -> list[dict]:
    """每张卡 -> 该卡用的服装。

    优先级：
    1) 数据库 card_dress 表（可手工覆盖，用于让新衣服顶替旧衣服显示）
    2) master 推导：该角色的主服装（costume_type=1 且 general_purpose=1，取最小 id）
    """
    try:
        mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        rows = mc.execute(
            "SELECT chara_id, MIN(id) FROM dress_data "
            "WHERE costume_type=1 AND general_purpose=1 GROUP BY chara_id").fetchall()
        main_dress = {r[0]: r[1] for r in rows}
        cards = mc.execute("SELECT id, chara_id FROM card_data ORDER BY id").fetchall()
        mc.close()
    except Exception:
        return []

    # 数据库覆盖
    override: dict[int, int] = {}
    try:
        with db() as con:
            for cid, did in con.execute("SELECT card_id, dress_id FROM card_dress").fetchall():
                if isinstance(cid, int) and isinstance(did, int) and did > 0:
                    override[cid] = did
    except Exception:
        pass

    out = []
    for card_id, chara_id in cards:
        d = override.get(card_id) or main_dress.get(chara_id)
        if d:
            out.append({"card_id": card_id, "cloth_id": d})
    return out


# ---------- 支援卡 ----------

def all_support_cards(viewer_id: int) -> list[dict]:
    """从 master 生成全量支援卡列表（默认 0 级、0 破）。"""
    try:
        mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        rows = mc.execute(
            "SELECT id FROM support_card_data ORDER BY id").fetchall()
        mc.close()
    except Exception:
        return []
    ts = now_str()
    return [{
        "viewer_id": viewer_id,
        "support_card_id": r[0],
        "exp": 0,
        "limit_break_count": 0,
        "favorite_flag": 0,
        "stock": 0,
        "possess_time": ts,
        "create_time": ts,
    } for r in rows]


# ---------- 商店（item/show_exchange）----------

def render_show_exchange(template: dict) -> dict:
    """limit_list 从数据库读（兑换次数持久化），其余字段沿用模板。"""
    d = dict(template)
    try:
        with db() as con:
            rows = con.execute(
                "SELECT item_exchange_id, exchange_count, update_time "
                "FROM exchange_state ORDER BY item_exchange_id").fetchall()
        if rows:
            d["limit_list"] = [
                {"item_exchange_id": r[0], "exchange_count": r[1] or 0,
                 "update_time": r[2] or ""}
                for r in rows
            ]
    except Exception:
        pass
    return d


def apply_exchange(template: dict, req: dict | None) -> dict:
    """item/exchange：兑换后累加 exchange_count。"""
    if isinstance(req, dict):
        eid = req.get("exchange_id")
        cnt = req.get("count") or 1
        if isinstance(eid, int):
            ts = now_str()
            with db() as con:
                con.execute(
                    "INSERT INTO exchange_state(item_exchange_id, exchange_count, update_time) "
                    "VALUES (?,?,?) ON CONFLICT(item_exchange_id) DO UPDATE SET "
                    "exchange_count = exchange_count + ?, update_time = ?",
                    (eid, cnt, ts, cnt, ts))
                con.commit()
    return dict(template)


# ---------- 写操作落库 ----------

def apply_save_chara(template: dict, req: dict | None) -> dict:
    """note/save_chara_data：更新角色服装（请求里带 chara_id + dress_id）。

    同时刷新 note/get_new_chara_data 缓存里的 dress_id —— 否则游戏下次请求
    该接口会拿到录制时的旧服装，把刚换的装覆盖回校服。
    """
    if isinstance(req, dict):
        cid = req.get("chara_id")
        dres = req.get("dress_id")
        mini = req.get("mini_dress_id")
        dcol = req.get("dress_color_id")
        mcol = req.get("mini_dress_color_id")
        if isinstance(cid, int) and isinstance(dres, int):
            save_chara_dress(cid, dres)
            _sync_new_chara_dress(dres, mini, dcol, mcol)
    d = dict(template)
    d.setdefault("data", {})
    return d


def _sync_new_chara_dress(dress_id: int, mini=None, dcol=None, mcol=None) -> None:
    """把 note/get_new_chara_data 缓存里的服装字段改成最新的。"""
    try:
        import msgpack as _mp
        with db() as con:
            row = con.execute(
                "SELECT data FROM response_cache WHERE path='note/get_new_chara_data'").fetchone()
            if not row or not row[0]:
                return
            obj = _mp.unpackb(row[0], raw=False, strict_map_key=False,
                              unicode_errors="replace")
            dd = obj.get("data")
            if not isinstance(dd, dict):
                return
            dd["dress_id"] = dress_id
            if isinstance(mini, int):
                dd["mini_dress_id"] = mini
            if isinstance(dcol, int):
                dd["dress_color_id"] = dcol
            if isinstance(mcol, int):
                dd["mini_dress_color_id"] = mcol
            nb = _mp.packb(obj, use_bin_type=True)
            con.execute("UPDATE response_cache SET data=?, declared=? "
                        "WHERE path='note/get_new_chara_data'", (nb, len(nb)))
            con.execute("UPDATE path_declared SET declared=? "
                        "WHERE path='note/get_new_chara_data'", (len(nb),))
            con.commit()
    except Exception as e:
        print(f"[db] 同步 new_chara 服装失败: {e}")


def apply_favorite(template: dict, req: dict | None) -> dict:
    """user/change_favorite_character：记录主页位置。

    请求形状：{"set_position_info": {position1_chara_id: .., position1_cloth_id: ..}}
    兼容旧形状（字段平铺在顶层）。
    """
    if isinstance(req, dict):
        src = req.get("set_position_info")
        if not isinstance(src, dict):
            src = req
        pos = {}
        for i in range(1, 5):
            cid = src.get(f"position{i}_chara_id")
            did = src.get(f"position{i}_cloth_id")
            col = src.get(f"position{i}_cloth_color_id")
            if isinstance(cid, int) and cid > 0:
                pos[f"position{i}_chara_id"] = cid
                pos[f"position{i}_cloth_id"] = did if isinstance(did, int) else 0
                pos[f"position{i}_cloth_color_id"] = col if isinstance(col, int) else 0
        if pos:
            save_home_layout(pos)
            set_state("home_position_info", json.dumps(pos, ensure_ascii=False))
    d = dict(template)
    lay = home_layout()
    if lay:
        d["data"] = {"home_position_info": lay}
    else:
        hp = get_state("home_position_info")
        if hp:
            try:
                d["data"] = {"home_position_info": json.loads(hp)}
            except Exception:
                pass
    return d


def apply_mission_receive(template: dict, req: dict | None) -> dict:
    """mission/receive：把响应里的 add_fcoin 真实加进 user_state。"""
    d = dict(template)
    rs = (d.get("data") or {}).get("reward_summary_info") or {}
    add_f = rs.get("add_fcoin") or 0
    if isinstance(add_f, int) and add_f > 0:
        cur = int(get_state("fcoin", "0"))
        set_state("fcoin", cur + add_f)
    return d


# ---------- 音乐 / Live ----------

def all_music() -> list[dict]:
    """从 master 的 jukebox_music_data 生成全量音乐列表（is_hidden=0）。"""
    try:
        mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        rows = mc.execute(
            "SELECT music_id FROM jukebox_music_data "
            "WHERE is_hidden=0 ORDER BY sort, music_id").fetchall()
        mc.close()
    except Exception:
        return []
    ts = now_str()
    return [{"music_id": r[0], "acquisition_time": ts} for r in rows]


# ---------- 道具 ----------

def all_items() -> list[dict]:
    """从 owned_item 读道具（item_id + number）。"""
    try:
        with db() as con:
            rows = con.execute("SELECT item_id, number FROM owned_item ORDER BY item_id").fetchall()
        return [{"item_id": r[0], "number": r[1]} for r in rows]
    except Exception:
        return []


# ---------- load/index ----------

def render_load_index(template: dict) -> dict:
    """基于模板重建 load/index 的 data 部分。"""
    d = dict(template)

    d["chara_list"] = all_chara()
    d["card_list"] = all_card()
    d["cloth_list"] = all_cloth()
    d["event_data_array"] = all_events()
    d["character_story_data_list"] = all_story_state()

    # 金币/道具
    coin = int(get_state("coin", "0"))
    fcoin = int(get_state("fcoin", "0"))
    d["coin_info"] = {"coin": coin, "fcoin": fcoin}

    # 道具：优先用 owned_item 表
    items_db = all_items()
    if items_db:
        by_id = {it["item_id"]: it for it in items_db}
        # 金币/钥匙以 user_state 为准
        for iid, key, dflt in ((59, "gold_item", 0), (190, "key_item", 0)):
            v = int(get_state(key, str(dflt)))
            if iid in by_id:
                by_id[iid]["number"] = v
            else:
                items_db.append({"item_id": iid, "number": v})
        d["item_list"] = sorted(items_db, key=lambda x: x["item_id"])
    else:
        il = d.get("item_list")
        if not isinstance(il, list):
            il = []
        by_id = {it.get("item_id"): it for it in il if isinstance(it, dict)}
        for iid, key in ((59, "gold_item"), (190, "key_item")):
            v = int(get_state(key, "0"))
            if iid in by_id:
                by_id[iid]["number"] = v
            else:
                il.append({"item_id": iid, "number": v})
        d["item_list"] = il

    # 清除所有菜单红点 / New 标记
    FUTURE = 1795000000  # 2026-11-19 之后
    lct = d.get("user_last_checked_time_list")
    if isinstance(lct, list):
        for it in lct:
            if isinstance(it, dict):
                it["last_checked_time"] = FUTURE
    d["new_trainer_skill_last_check_time"] = FUTURE
    d["new_plushie_exists"] = False
    badge = d.get("menu_badge_info")
    if isinstance(badge, dict):
        for k in list(badge.keys()):
            v = badge[k]
            if isinstance(v, int):
                badge[k] = 0
            elif isinstance(v, list):
                badge[k] = []
            elif isinstance(v, bool):
                badge[k] = False

    # 大厅编组（从 chara_layout 读，编辑器改完重启游戏生效）
    lay = home_layout()
    if lay:
        d["home_position_info"] = lay

    # 关闭训练挑战入口（该活动接口响应结构不确定，开了必软死）
    d["training_challenge_user_info"] = None
    d["training_challenge_exam_infos"] = []
    d["challenge_match_load_info"] = None
    d["training_report_info"] = None

    # 卡的默认服装映射（全量）
    cda = all_card_dress()
    if cda:
        old_cda = d.get("card_dress_array")
        if isinstance(old_cda, list) and len(old_cda) > len(cda):
            pass  # 保留更完整的旧数据
        else:
            d["card_dress_array"] = cda

    # 支援卡列表：以 master 全量为底，保留录制里已有的 exp/突破
    try:
        vid = int(get_state("viewer_id", "601653962"))
    except Exception:
        vid = 601653962
    old_sc = d.get("support_card_list")
    old_map = {}
    if isinstance(old_sc, list):
        for sc in old_sc:
            if isinstance(sc, dict) and sc.get("support_card_id"):
                old_map[sc["support_card_id"]] = sc
    new_sc = all_support_cards(vid)
    if new_sc:
        for sc in new_sc:
            prev = old_map.get(sc["support_card_id"])
            if prev:
                for k in ("exp", "limit_break_count", "favorite_flag",
                          "stock", "possess_time", "create_time"):
                    if k in prev:
                        sc[k] = prev[k]
        d["support_card_list"] = new_sc

    # 碎片列表：master 全量卡 + 保留已有数量
    try:
        mc2 = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        _piece_ids = [r[0] for r in mc2.execute(
            "SELECT id FROM card_data ORDER BY id").fetchall()]
        mc2.close()
    except Exception:
        _piece_ids = []
    if _piece_ids:
        old_pc = d.get("piece_list")
        pc_map = {}
        if isinstance(old_pc, list):
            for pc in old_pc:
                if isinstance(pc, dict) and pc.get("piece_id"):
                    pc_map[pc["piece_id"]] = pc.get("piece_num", 0)
        d["piece_list"] = [{"piece_id": pid, "piece_num": pc_map.get(pid, 0)}
                           for pid in _piece_ids]

    # 音乐列表（全量，含新实装的 live）
    mus = all_music()
    if mus:
        d["music_list"] = mus

    # release_card_array 与 card_list 对齐
    d["release_card_array"] = sorted(c["card_id"] for c in d["card_list"])

    # chara_profile_array 只保留拥有角色的
    prof = d.get("chara_profile_array")
    if isinstance(prof, list):
        owned = {c["chara_id"] for c in d["chara_list"]}
        d["chara_profile_array"] = [p for p in prof
                                    if isinstance(p, dict) and p.get("chara_id") in owned]

    # 殿堂（名鉴）走的是 load/index 的精简请求，键名是 trained_chara_array（多 _array）
    # 所以两个键都要给，否则客户端读不到会报「无法读取数据」
    d["trained_chara_array"] = d.get("trained_chara") or []
    d.setdefault("room_match_entry_chara_id_array", [])
    d.setdefault("compare_source_array", [])

    return d


# ---------- note/index ----------

def render_note_index(template: dict) -> dict:
    d = dict(template)
    cards = sorted(c["card_id"] for c in all_card())
    d["release_card_array"] = cards
    return d


# ---------- note/use_gallery_key ----------

def unlock_events(story_ids: list[int]) -> dict:
    """解锁事件 + 扣钥匙，返回响应 data。"""
    if not story_ids:
        return {"item_info_array": [], "event_data_array": [], "home_story_data_array": []}

    mc = master()
    mcur = mc.cursor()
    ph = ",".join("?" * len(story_ids))
    mcur.execute(
        f"SELECT story_id, card_chara_id FROM single_mode_story_data "
        f"WHERE gallery_flag=1 AND story_id IN ({ph})", story_ids)
    valid = {r[0]: r[1] for r in mcur.fetchall()}
    mc.close()

    unlocked = []
    ts = now_str()
    with db() as con:
        for sid in story_ids:
            cid = valid.get(sid)
            if cid is None:
                continue
            con.execute(
                "INSERT OR IGNORE INTO unlocked_event(story_id, chara_id, unlocked_at, new_flag) "
                "VALUES (?,?,?,0)", (sid, cid, ts))
            unlocked.append({"chara_id": cid, "data_id": sid,
                             "create_time": ts, "new_flag": 0})
        con.commit()

    key = int(get_state("key_item", "0"))
    key = max(0, key - len(unlocked))
    set_state("key_item", key)

    return {
        "item_info_array": [{"item_id": 190, "number": key}],
        "event_data_array": unlocked,
        "home_story_data_array": [],
    }


# ---------- note/save_chara_data（换装） ----------

def save_chara_dress(chara_id: int, dress_id: int) -> bool:
    with db() as con:
        cur = con.execute("UPDATE owned_chara SET dress_id=? WHERE chara_id=?",
                          (dress_id, chara_id))
        con.commit()
        return cur.rowcount > 0


# ---------- 剧情内容 ----------

def event_content(story_id: int, select_index: int = 0) -> dict | None:
    mc = master()
    mcur = mc.cursor()
    mcur.execute("SELECT card_chara_id, event_category FROM single_mode_story_data "
                 "WHERE story_id=?", (story_id,))
    row = mcur.fetchone()
    mc.close()
    if not row:
        return None
    chara_id, cat = row
    return {
        "response_code": 1,
        "data_headers": {"result_code": 1, "servertime": int(time.time())},
        "data": {
            "event_id": (cat + 1) * 1000,
            "chara_id": chara_id,
            "story_id": story_id,
            "event_contents_info": {
                "support_card_id": 0,
                "choice_array": [{
                    "select_index_info_array": [{"branch_number": 1,
                                                 "select_index": 1}],
                    "receive_item_id": 0,
                    "target_race_id": 0,
                    "gain_select_id_index": 1,
                    "select_icon": 0,
                }],
                "month": 4,
                "race_id": 0,
            },
        },
    }


# ---------- 已拥有卡列表（card/get_release_card_array）----------

def render_release_card_array(template: dict) -> dict:
    d = dict(template)
    d["release_card_array"] = sorted(c["card_id"] for c in all_card())
    return d


# ---------- 道具 + 事件（item_info_array_number）----------

def render_item_info(template: dict) -> dict:
    d = dict(template)
    gold = int(get_state("gold_item", "0"))
    key = int(get_state("key_item", "0"))
    d["item_info_array"] = [
        {"item_id": 59, "number": gold},
        {"item_id": 190, "number": key},
    ]
    d["event_data_array"] = all_events()
    d.setdefault("home_story_data_array", [])
    return d


# ---------- 散步（const_walking/index）----------

def render_walking(template: dict) -> dict:
    """从 master.campaign_walking_chara 生成散步解锁记录。"""
    d = dict(template)
    try:
        mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        # 每个角色的 location 去重（每角色应有 12 条 = 12/12）
        rows = mc.execute(
            "SELECT chara_id, location_1, location_2, location_3 "
            "FROM campaign_walking_chara").fetchall()
        valid_loc = {r[0] for r in mc.execute(
            "SELECT id FROM campaign_walking_location").fetchall()}
        mc.close()
    except Exception:
        return d

    per: dict[int, list[int]] = {}
    for cid, l1, l2, l3 in rows:
        lst = per.setdefault(cid, [])
        for v in (l1, l2, l3):
            if v and v in valid_loc and v not in lst:
                lst.append(v)

    ts = now_str()
    arr = []
    for cid in sorted(per):
        for loc in sorted(per[cid]):
            arr.append({
                "chara_id": cid,
                "data_id": loc,
                "create_time": ts,
                "new_flag": 0,
            })
    if arr:
        d["chara_walking_act_array"] = arr
    return d


# ---------- 卡池列表（gacha/index）----------

def visible_gachas() -> list[int]:
    """返回被勾选显示的 gacha_id（按 sort）。"""
    try:
        with db() as con:
            rows = con.execute(
                "SELECT gacha_id FROM gacha_visible WHERE enabled=1 "
                "ORDER BY sort, gacha_id").fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def render_gacha_index(template_data: dict) -> dict:
    """按 gacha_visible 渲染 gacha/index。

    模板里 gacha_info_list 的每条都有完整字段，这里复制模板首条，
    只把 id 换成勾选的 gacha_id。
    """
    d = dict(template_data)
    old_list = d.get("gacha_info_list") or []
    tpl_item = dict(old_list[0]) if old_list else {
        "id": 0, "is_daily_draw_end": 0,
        "prize_selected_card_type": 0, "prize_selected_card_id": 0,
        "is_campaign_draw_enable_single": 0, "is_campaign_draw_enable_multi": 0,
        "remain_stock_num_single": 0, "remain_stock_num_multi": 0,
        "web_text": "", "remain_paid_draw_num": 0,
        "is_continuous_daily_gacha": 0, "continuous_daily_gacha_count": 0,
        "is_campaign_draw_enable_continuous_daily": 0,
    }
    # 保留模板里原有的每个池的个性化字段
    by_id = {gi.get("id"): gi for gi in old_list if isinstance(gi, dict)}

    ids = visible_gachas()
    if not ids:
        d["gacha_info_list"] = old_list
        return d

    new_list = []
    for gid in ids:
        base = by_id.get(gid)
        if base:
            new_list.append(base)
        else:
            item = dict(tpl_item)
            item["id"] = gid
            new_list.append(item)
    d["gacha_info_list"] = new_list
    return d


# ---------- 抽卡 ----------

def record_gacha(gacha_id: int, results: list[dict]) -> None:
    ts = now_str()
    with db() as con:
        for r in results:
            con.execute(
                "INSERT INTO gacha_log(gacha_id, card_type, card_id, new_flag, drawn_at) "
                "VALUES (?,?,?,?,?)",
                (gacha_id, r.get("card_type", 1), r.get("card_id", 0),
                 r.get("new_flag", 0), ts))
        con.commit()


def stats() -> dict:
    with db() as con:
        out = {}
        for t in ("owned_chara", "owned_card", "owned_cloth",
                  "unlocked_event", "story_state", "gacha_log"):
            out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return out


if __name__ == "__main__":
    print("数据库统计:", stats())
    print("coin =", get_state("coin"), "fcoin =", get_state("fcoin"))
    print("key =", get_state("key_item"), "gold =", get_state("gold_item"))


# ---------- 数据同步（写操作 → 读接口） ----------

def render_gacha_history(data: dict) -> dict:
    """gacha/get_history：从 gacha_log 重建抽卡历史（接收 data，返回 data）。"""
    d = dict(data) if isinstance(data, dict) else {}
    try:
        with db() as con:
            con.row_factory = sqlite3.Row
            logs = con.execute(
                "SELECT id, gacha_id, card_type, card_id, new_flag, drawn_at "
                "FROM gacha_log ORDER BY id DESC LIMIT 20").fetchall()
    except Exception:
        return d

    exec_arr = []
    reward_arr = []
    base_id = 900
    for i, r in enumerate(logs):
        eid = base_id + (r["id"] or 0)
        exec_arr.append({
            "exec_history_id": eid,
            "gacha_id": r["gacha_id"] or 0,
            "gacha_card_type": r["card_type"] or 1,
            "draw_type": 1,
            "draw_num": 1,
            "cost_id": 0,
            "cost_count": 150,
            "create_time": r["drawn_at"] or "2026-01-01 00:00:00",
        })
        reward_arr.append({
            "exec_history_id": eid,
            "disp_order": 1,
            "card_type": r["card_type"] or 1,
            "card_id": r["card_id"] or 0,
            "piece_id": r["card_id"] or 0,
            "common_item_category": 97,
            "common_item_id": 115,
            "convert_piece_num": 0,
            "convert_common_item_num": 1,
            "additional_piece_num": 5,
        })
    if exec_arr:
        d["gacha_exec_history_array"] = exec_arr
        d["gacha_reward_history_array"] = reward_arr
    return d


def apply_save_voice(template: dict, req: dict | None) -> dict:
    """note/save_voice：记录语音收藏（chara_id + voice_id/data_id）。"""
    if isinstance(req, dict):
        try:
            cid = req.get("chara_id")
            vid = req.get("voice_id") or req.get("data_id") or req.get("voice_data_id")
            flag = req.get("new_flag")
            if isinstance(cid, int) and isinstance(vid, int):
                with db() as con:
                    con.execute(
                        "INSERT OR REPLACE INTO voice_favorite(chara_id, voice_id, new_flag, updated_at) "
                        "VALUES (?,?,?,datetime('now'))",
                        (cid, vid, flag if isinstance(flag, int) else 0))
                    con.commit()
                # 同步 note/get_new_chara_data 里的 voice_data_array
                _sync_voice_flag(cid, vid, flag if isinstance(flag, int) else 0)
        except Exception as e:
            print(f"[db] save_voice 落库失败: {e}")
    d = dict(template)
    d.setdefault("data", {})
    return d


def _sync_voice_flag(chara_id: int, voice_id: int, new_flag: int) -> None:
    """把 note/get_new_chara_data 缓存里对应语音的 new_flag 改掉。"""
    try:
        import msgpack as _mp
        with db() as con:
            row = con.execute(
                "SELECT data FROM response_cache WHERE path='note/get_new_chara_data'").fetchone()
            if not row or not row[0]:
                return
            obj = _mp.unpackb(row[0], raw=False, strict_map_key=False,
                              unicode_errors="replace")
            arr = (obj.get("data") or {}).get("voice_data_array")
            if not isinstance(arr, list):
                return
            changed = False
            for it in arr:
                if (isinstance(it, dict) and it.get("chara_id") == chara_id
                        and it.get("data_id") == voice_id):
                    if it.get("new_flag") != new_flag:
                        it["new_flag"] = new_flag
                        changed = True
                    break
            if changed:
                nb = _mp.packb(obj, use_bin_type=True)
                con.execute("UPDATE response_cache SET data=?, declared=? "
                            "WHERE path='note/get_new_chara_data'", (nb, len(nb)))
                con.execute("UPDATE path_declared SET declared=? "
                            "WHERE path='note/get_new_chara_data'", (len(nb),))
                con.commit()
    except Exception as e:
        print(f"[db] 同步 voice_flag 失败: {e}")


def apply_jukebox_like(template: dict, req: dict | None) -> dict:
    """jukebox/exec_like：记录点赞状态。"""
    if isinstance(req, dict):
        try:
            rid = req.get("request_id")
            if isinstance(rid, int):
                cur = int(get_state("jukebox_like_count", "0"))
                set_state("jukebox_like_count", cur + 1)
                set_state("jukebox_liked_request", str(rid))
        except Exception as e:
            print(f"[db] exec_like 落库失败: {e}")
    d = dict(template)
    d.setdefault("data", {})
    return d


def sync_jukebox_index(obj: dict, viewer_id: int) -> dict:
    """jukebox/index：把录制号主的值换成真实值。"""
    dd = obj.get("data")
    if not isinstance(dd, dict):
        return obj
    try:
        liked = get_state("jukebox_liked_request", "")
        lc = int(get_state("jukebox_like_count", "0"))
    except Exception:
        liked, lc = "", 0
    rh = dd.get("request_history")
    if isinstance(rh, dict):
        # requester_id 是角色 id，不是 viewer_id；保留
        pass
    dd["like_count"] = 12 + lc
    if liked:
        try:
            dd["is_liked"] = (int(liked) == (rh or {}).get("request_id"))
        except Exception:
            dd["is_liked"] = False
    return obj


# ---------- 角色编组（大厅 / Live） ----------

def home_layout() -> dict:
    """从 chara_layout 读大厅编组，返回 home_position_info 结构。"""
    out = {}
    with db() as con:
        rows = con.execute(
            "SELECT position, chara_id, dress_id, color_id FROM chara_layout "
            "WHERE kind='home' ORDER BY position").fetchall()
    for pos, cid, did, col in rows:
        out[f"position{pos}_chara_id"] = cid or 0
        out[f"position{pos}_cloth_id"] = did or 0
        out[f"position{pos}_cloth_color_id"] = col or 0
    return out


def save_home_layout(items: dict) -> int:
    """把 {positionN_chara_id, positionN_cloth_id, ...} 写进 chara_layout。"""
    n = 0
    with db() as con:
        for i in range(1, 5):
            cid = items.get(f"position{i}_chara_id")
            if not isinstance(cid, int) or cid <= 0:
                continue
            con.execute(
                "INSERT OR REPLACE INTO chara_layout(kind, slot, position, chara_id, dress_id, color_id) "
                "VALUES ('home', 1, ?, ?, ?, ?)",
                (i, cid,
                 items.get(f"position{i}_cloth_id") or 0,
                 items.get(f"position{i}_cloth_color_id") or 0))
            n += 1
        con.commit()
    return n


def live_presets() -> list[dict]:
    """从 chara_layout 组装 preset_array（保持 preset_id / 名称顺序）。"""
    with db() as con:
        names_row = con.execute("SELECT value FROM meta WHERE key='live_preset_names'").fetchone()
        names = {}
        if names_row and names_row[0]:
            try:
                names = json.loads(names_row[0])
            except Exception:
                names = {}
        rows = con.execute(
            "SELECT slot, position, chara_id, dress_id, color_id, dress_id2, color_id2, mob_id "
            "FROM chara_layout WHERE kind='live' ORDER BY slot, position").fetchall()

    presets: dict[int, list] = {}
    for slot, pos, cid, did, col, did2, col2, mob in rows:
        presets.setdefault(slot, []).append({
            "chara_id": cid or 0,
            "mob_id": mob or 0,
            "dress_id": did or 0,
            "dress_id2": did2 or 0,
            "color_id": col or 0,
            "color_id2": col2 or 0,
        })

    out = []
    for pid in sorted(presets):
        out.append({
            "preset_id": pid,
            "preset_name": names.get(str(pid), f"编组{pid}"),
            "member_info_array": presets[pid],
        })
    return out


def render_live_preset(data: dict) -> dict:
    """live_theater_performers_preset/index：用 chara_layout 的编组覆盖预设。"""
    d = dict(data) if isinstance(data, dict) else {}
    arr = live_presets()
    if arr:
        d["preset_array"] = arr
    return d


# ---------- 转籍 ----------

def render_transfer_exec(data: dict) -> dict:
    """transfer/rotation_exec_multi：执行一次转籍。

    每调一次：把第一个 remaining_num > 0 的档位减 1，返回同一份奖励。
    没有剩余次数时保持原样（返回 0 变化）。
    """
    d = json.loads(json.dumps(data)) if isinstance(data, dict) else {}
    info = d.get("transfer_rotation_info")
    if not isinstance(info, dict):
        return d
    details = info.get("transfer_rotation_home_detail_info")
    if not isinstance(details, list):
        return d

    used = None
    with db() as con:
        for item in details:
            did = item.get("transfer_detail_id")
            row = con.execute(
                "SELECT remaining_num FROM transfer_rotation_state WHERE transfer_detail_id=?",
                (did,)).fetchone()
            if row is None:
                con.execute("INSERT OR REPLACE INTO transfer_rotation_state("
                            "transfer_detail_id, remaining_num, updated_at) VALUES (?,?,datetime('now'))",
                            (did, item.get("remaining_num") or 0))
                row = (item.get("remaining_num") or 0,)
            remain = int(row[0])
            item["remaining_num"] = remain
            item["exists_trained_chara"] = remain > 0
            if remain > 0 and used is None:
                used = did
        if used is not None:
            con.execute("UPDATE transfer_rotation_state SET remaining_num = remaining_num - 1, "
                        "updated_at = datetime('now') WHERE transfer_detail_id=?", (used,))
            for item in details:
                if item.get("transfer_detail_id") == used:
                    item["remaining_num"] = max(0, (item.get("remaining_num") or 0) - 1)
                    item["exists_trained_chara"] = item["remaining_num"] > 0
        con.commit()

    print(f"[transfer] exec_multi 使用档位 {used}")
    return d


# ---------- 比赛预设（练习赛 / 房间赛） ----------

def race_presets(kind: str) -> list[dict]:
    """从 preset_race 组装预设列表。"""
    with db() as con:
        names_row = con.execute(
            "SELECT value FROM meta WHERE key=?", (f"{kind}_preset_names",)).fetchone()
        names = {}
        if names_row and names_row[0]:
            try:
                names = json.loads(names_row[0])
            except Exception:
                names = {}
        rows = con.execute(
            "SELECT preset_id, position, chara_id, dress_id FROM preset_race "
            "WHERE kind=? ORDER BY preset_id, position", (kind,)).fetchall()

    by_id: dict[int, list] = {}
    for pid, pos, cid, did in rows:
        by_id.setdefault(pid, []).append({"chara_id": cid, "dress_id": did})

    out = []
    for pid in sorted(by_id):
        out.append({
            "preset_id": pid,
            "name": names.get(str(pid), f"出走リスト{pid}"),
            "preset_chara_array": by_id[pid],
        })
    return out


def render_practice_preset(data: dict) -> dict:
    """practice_race/get_preset_array：用 preset_race 的编成覆盖。"""
    d = json.loads(json.dumps(data)) if isinstance(data, dict) else {}
    arr = race_presets("practice")
    if arr:
        # 保留原预设的数量与名字，只换成员
        old = d.get("preset_info_array")
        if isinstance(old, list) and len(old) >= len(arr):
            by_id = {p["preset_id"]: p for p in arr}
            for p in old:
                hit = by_id.get(p.get("preset_id"))
                if hit:
                    p["preset_chara_array"] = hit["preset_chara_array"]
            d["preset_info_array"] = old
        else:
            d["preset_info_array"] = arr
    return d


def render_room_preset(data: dict) -> dict:
    """room_match/get_preset_array：同上，但字段是 preset_array。"""
    d = json.loads(json.dumps(data)) if isinstance(data, dict) else {}
    arr = race_presets("room")
    if arr:
        d["preset_array"] = arr
    return d


# ---------- 社团聊天 ----------

def _chat_user_info() -> dict:
    """当前玩家的聊天用户信息（社团里显示的头像/名字）。"""
    lay = home_layout()
    cid = lay.get("position1_chara_id") or 1114
    did = lay.get("position1_cloth_id") or 111401
    return {"viewer_id": VIEWER_ID, "leader_chara_id": cid,
            "leader_chara_dress_id": did, "name": "RiceShower"}


def append_chat(viewer_id: int, message_type: int, message_id: int) -> dict:
    """写一条聊天记录，返回该条消息。"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with db() as con:
        cur = con.execute(
            "INSERT INTO circle_chat_log(viewer_id, message_type, message_id, display, create_time) "
            "VALUES (?,?,?,1,?)", (viewer_id, message_type, message_id, ts))
        pid = 1000 + cur.lastrowid
        con.commit()
    return {"post_id": pid, "viewer_id": viewer_id, "message_type": message_type,
            "message_id": message_id, "display": 1, "create_time": ts}


def chat_messages(limit: int = 50) -> list[dict]:
    with db() as con:
        rows = con.execute(
            "SELECT post_id, viewer_id, message_type, message_id, display, create_time "
            "FROM circle_chat_log ORDER BY post_id DESC LIMIT ?", (limit,)).fetchall()
    out = [{"post_id": r[0], "viewer_id": r[1], "message_type": r[2],
            "message_id": r[3], "display": r[4], "create_time": r[5]} for r in rows]
    out.reverse()
    return out


def render_send_stamp(template: dict, req: dict | None) -> dict:
    """circle_chat/send_stamp：只能原样回放。

    实测：改 message_id / post_id / create_time 任意一个都会让客户端报
    「无法读取服务器数据」，说明这些字段在客户端有校验。
    因此固定返回录制那一条（stamp 100139）。
    """
    return template

def render_chat_polling(template: dict) -> dict:
    """circle_chat/polling：保留录制里的历史消息，后面追加新发的。"""
    import copy as _copy
    d = _copy.deepcopy(template) if isinstance(template, dict) else {}
    dd = d.get("data")
    if not isinstance(dd, dict):
        dd = {}
        d["data"] = dd
    base = dd.get("circle_chat_message_array")
    base = list(base) if isinstance(base, list) else []
    extra = chat_messages()
    # 去重：post_id 不重复
    have = {m.get("post_id") for m in base if isinstance(m, dict)}
    base.extend(m for m in extra if m.get("post_id") not in have)
    dd["circle_chat_message_array"] = base
    dd["circle_chat_user_array"] = [_chat_user_info()]
    dd["circle_item_request_array"] = []
    dd["circle_item_donate_array"] = []
    dd["room_match_info_array"] = []
    dd["circle_post_partner_array"] = []
    dd["chat_polling_interval"] = 3
    return d


def render_live_theater(data: dict) -> dict:
    """live_theater/index：把 last_checked_time 推到未来，去掉 New 标。"""
    d = json.loads(json.dumps(data)) if isinstance(data, dict) else {}
    if "live_theater_last_checked_time" in d:
        d["live_theater_last_checked_time"] = 1795000000
    return d
