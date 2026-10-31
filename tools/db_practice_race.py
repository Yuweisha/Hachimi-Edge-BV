"""练习赛（practice_race）动态生成。

与传奇赛的关键差异（实测请求 / 响应结构）：

  请求 practice_race/race_start 里信息很全：
    {race_instance_id, season, weather, ground_condition, motivation, entry_num,
     entry_chara_array: [{viewer_id, trained_chara_id, running_style, entry_id, use_type}]}

  响应剧本位置也不同：
    data.race_result_info.race_scenario      ← 不是 data.race_scenario
    data.race_result_info.race_horse_data_array  （49 字段，比 race_entry 多一个）

对手来源：
  练习赛的 race_instance.npc_group_id（如 1004）在 NPC 表里只有个位数记录，
  凑不满 entry_num 匹 —— 说明练习赛本来就是随机对手，因此这里用 npc_gen 合成。

赛道：
  race_instance_id → race_instance.race_id → race.course_set
    → race_course_set.distance / finish_time_max
"""
import copy
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/tools")
UMA_DIR = Path(r"C:/Users/Schwarz/uma_replay")
MDB = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb"

if str(UMA_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(UMA_DIR))


def _course_of(race_instance_id: int):
    """race_instance_id → (distance, t_ref, ground, turn)"""
    try:
        con = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        r = con.execute("""
            SELECT rcs.distance, rcs.finish_time_max, rcs.ground, rcs.turn
            FROM race_instance ri
            JOIN race r ON r.id = ri.race_id
            JOIN race_course_set rcs ON rcs.id = r.course_set
            WHERE ri.id = ?
        """, (int(race_instance_id),)).fetchone()
        con.close()
        if r:
            # finish_time_max 是 ×10000 的定点（2040000 → 204.0 秒）
            return float(r[0]), round(r[1] / 10000.0, 3), int(r[2]), int(r[3])
    except Exception:
        pass
    return None


def _trained_attrs(con: sqlite3.Connection, trained_chara_id: int | None):
    """从 load/index 取玩家马的属性。"""
    if not trained_chara_id:
        return None
    import msgpack
    r = con.execute("SELECT data FROM response_cache WHERE path='load/index'").fetchone()
    if not r:
        return None
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    arr = ((obj.get("data") or {}).get("trained_chara") or [])
    for t in arr:
        if t.get("trained_chara_id") == trained_chara_id:
            return t
    return None


def build_practice_race_start(con: sqlite3.Connection, req: dict | None):
    """返回 (data_dict, note)。失败返回 (None, reason)。

    req 必须包含 race_instance_id / entry_num / entry_chara_array。
    """
    import msgpack
    import npc_gen          # 供 make_opponents / random_motivation 使用
    req = req or {}
    ri_id = req.get("race_instance_id")
    if not ri_id:
        return None, "请求缺 race_instance_id"

    entry_num = int(req.get("entry_num") or 0)
    entry = (req.get("entry_chara_array") or [{}])[0]
    tcid = entry.get("trained_chara_id")
    my_style = int(entry.get("running_style") or 2)

    course = _course_of(ri_id)
    if not course:
        return None, f"race_instance_id={ri_id} 查不到赛道"
    distance, t_ref, ground, _turn = course

    # 模板：现有缓存的 practice_race/race_start（结构齐全）
    r = con.execute(
        "SELECT data FROM response_cache WHERE path='practice_race/race_start'").fetchone()
    if not r:
        return None, "库里没有 practice_race/race_start 模板"
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    data = copy.deepcopy(obj.get("data") or {})
    info = data.get("race_result_info") or {}
    hs_tpl = info.get("race_horse_data_array") or []
    if not hs_tpl:
        return None, "模板里没有 race_horse_data_array"

    n = entry_num or len(hs_tpl)
    me = copy.deepcopy(hs_tpl[0])
    proto = copy.deepcopy(hs_tpl[0])     # 49 字段模板

    # --- 玩家马 ---
    t = _trained_attrs(con, tcid)
    if t:
        for k_src, k_dst in (("speed", "speed"), ("stamina", "stamina"),
                             ("power", "pow"), ("guts", "guts"), ("wiz", "wiz")):
            if t.get(k_src) is not None:
                me[k_dst] = int(t[k_src])
        if t.get("card_id"):
            me["card_id"] = t["card_id"]
            me["chara_id"] = int(t["card_id"]) // 100
        me["trained_chara_id"] = tcid
        me["viewer_id"] = entry.get("viewer_id") or 0
        for k in ("skill_array", "race_dress_id", "nickname_id",
                  "proper_distance_short", "proper_distance_mile",
                  "proper_distance_middle", "proper_distance_long",
                  "proper_running_style_nige", "proper_running_style_senko",
                  "proper_running_style_sashi", "proper_running_style_oikomi",
                  "proper_ground_turf", "proper_ground_dirt",
                  "win_saddle_id_array", "talent_level", "rarity"):
            if t.get(k) is not None:
                me[k] = copy.deepcopy(t[k])
    me["running_style"] = my_style
    me["motivation"] = npc_gen.random_motivation()   # 所有角色干劲随机
    me["frame_order"] = 1

    # --- 对手：随机合成 ---
    pspd = int(me.get("speed") or 1500)
    opps = npc_gen.make_opponents(max(0, n - 1), band=None, player_speed=pspd,
                                  distance=distance, ground=ground, seed=None,
                                  avoid_chara={me.get("chara_id")})

    horses = [me]
    for i, o in enumerate(opps):
        h = copy.deepcopy(proto)
        h.update({
            "viewer_id": 0, "owner_viewer_id": 0, "trainer_name": None,
            "owner_trainer_name": "", "single_mode_chara_id": 0,
            "trained_chara_id": 0, "nickname_id": 0, "card_id": 0,
            "chara_id": o["chara_id"], "mob_id": 0, "rarity": 3, "talent_level": 1,
            "race_dress_id": o.get("dress_id") or 0,
            "skill_array": [],                    # 技能暂不生成（见文件头说明）
            "speed": o["speed"], "stamina": o["stamina"], "pow": o["pow"],
            "guts": o["guts"], "wiz": o["wiz"],
            "running_style": o["running_style"], "motivation": o["motivation"],
            "frame_order": i + 2,
            "popularity": i + 2,
            "popularity_mark_rank_array": [i + 2, i + 2, i + 2],
        })
        for k in ("proper_distance_short", "proper_distance_mile",
                  "proper_distance_middle", "proper_distance_long",
                  "proper_running_style_nige", "proper_running_style_senko",
                  "proper_running_style_sashi", "proper_running_style_oikomi",
                  "proper_ground_turf", "proper_ground_dirt"):
            if k in o:
                h[k] = o[k]
        horses.append(h)

    # 按 speed 降序排列（玩家可能在中间），再重排 frame_order
    import gen_race_full as _grf
    horses.sort(key=lambda x: -_grf.cruise_speed(int(x.get("speed") or 1000)))
    for i, h in enumerate(horses):
        h["frame_order"] = i + 1
        h["popularity"] = i + 1
    mypos = next((i for i, h in enumerate(horses)
                  if h.get("viewer_id") and h["viewer_id"] != 0), 0)

    # --- 剧本 ---
    speeds = [int(h.get("speed") or 1000) for h in horses]
    stams = [int(h.get("stamina") or 1000) for h in horses]
    styles = [int(h.get("running_style") or 2) for h in horses]

    scen = None
    _use_real = False
    try:
        _r = con.execute("SELECT value FROM meta WHERE key='use_real_model'").fetchone()
        _use_real = bool(_r and str(_r[0]) == "1")
    except Exception:
        pass
    if _use_real:
        try:
            # 真实解包模型
            _grade = {8: "S", 7: "A", 6: "B", 5: "C", 4: "D", 3: "E", 2: "F", 1: "G"}
            def _g(v, default="A"):
                try:
                    return _grade.get(int(v), default)
                except Exception:
                    return default
            _hd = []
            for h in horses:
                _hd.append({
                    "speed": int(h.get("speed") or 1000),
                    "stamina": int(h.get("stamina") or 1000),
                    "power": int(h.get("pow") or 1000),
                    "guts": int(h.get("guts") or 1000),
                    "wiz": int(h.get("wiz") or 1000),
                    "motivation": int(h.get("motivation") or 3),
                    "style": int(h.get("running_style") or 2),
                    "proper_distance_short": _g(h.get("proper_distance_short")),
                    "proper_distance_mile": _g(h.get("proper_distance_mile")),
                    "proper_distance_middle": _g(h.get("proper_distance_middle")),
                    "proper_distance_long": _g(h.get("proper_distance_long")),
                    "proper_ground_turf": _g(h.get("proper_ground_turf")),
                    "proper_ground_dirt": _g(h.get("proper_ground_dirt")),
                    "proper_running_style_nige": _g(h.get("proper_running_style_nige")),
                    "proper_running_style_senko": _g(h.get("proper_running_style_senko")),
                    "proper_running_style_sashi": _g(h.get("proper_running_style_sashi")),
                    "proper_running_style_oikomi": _g(h.get("proper_running_style_oikomi")),
                })
            import gen_race_real as _grr2
            scen = _grr2.build_real(_hd, float(distance), int(ground),
                                    int(req.get("ground_condition") or 1), t_ref=t_ref)
        except Exception as e:
            scen = None
            note_err = f"（scratch 失败: {e}）"
    if scen is None:
        # 回退：按模板结构重算（沿用模板帧数），至少保证马数/属性对齐
        try:
            import base64, gzip
            tpl = gzip.decompress(base64.b64decode(info.get("race_scenario") or ""))
            scen = _grf.build(tpl, speeds, stams, distance, player_pos=None, rank_gap=0.004)
        except Exception:
            scen = None

    if scen is None:
        return None, "剧本生成失败"

    import base64 as _b64, gzip as _gz
    info["race_scenario"] = _b64.b64encode(_gz.compress(scen, 6)).decode("ascii")
    info["race_horse_data_array"] = horses
    info["race_instance_id"] = ri_id
    info["season"] = req.get("season", info.get("season"))
    info["weather"] = req.get("weather", info.get("weather"))
    info["ground_condition"] = req.get("ground_condition", info.get("ground_condition"))
    data["race_result_info"] = info
    data["entry_info_array"] = [{"entry_id": 0, "frame_order": mypos + 1}]
    data["practice_race_id"] = req.get("practice_race_id") or data.get("practice_race_id")

    note = (f"练习赛 {n} 匹 / {distance:.0f}m / t_ref={t_ref}s / "
            f"玩家 idx={mypos} style={my_style} / 剧本 {len(scen):,} B")
    return data, note
