"""按客户端传入的 trained_chara_id，动态生成 ultimate_race/race_entry 响应。

流程：
    race_entry 请求 {ultimate_race_id, trained_chara_id}
      → 从 load/index 的 trained_chara 里查该 id 的属性
      → 用模板的 18 匹马，只替换「马 0」（玩家）
      → 返回新的 race_horse_data_array

用法（服务器内部调用）：
    from db_race_entry import build_race_entry
    data = build_race_entry(con, trained_chara_id)
"""
from __future__ import annotations

import copy
import sqlite3

# 名字不同的字段：race_entry 键 → trained_chara 键
_MAP = {
    "fan_count": "fans",
    "race_dress_id": "race_cloth_id",
    "final_grade": "rank",
    "race_result_array": "race_result_list",
}

# 名字相同的字段（直接搬）
_SAME = [
    "card_id", "rarity", "talent_level", "running_style",
    "speed", "stamina", "guts", "wiz",
    "nickname_id", "single_mode_chara_id",
    "skill_array", "win_saddle_id_array", "scenario_data_array",
    "proper_distance_short", "proper_distance_mile",
    "proper_distance_middle", "proper_distance_long",
    "proper_ground_turf", "proper_ground_dirt",
    "proper_running_style_nige", "proper_running_style_senko",
    "proper_running_style_sashi", "proper_running_style_oikomi",
]


def _find_trained(con: sqlite3.Connection, trained_chara_id: int):
    """从 load/index 模板里找该 trained_chara_id 的属性。"""
    import msgpack

    r = con.execute("SELECT data FROM response_cache WHERE path='load/index'").fetchone()
    if not r:
        return None
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    for t in (obj.get("data") or {}).get("trained_chara") or []:
        if t.get("trained_chara_id") == trained_chara_id:
            return t
    return None


def _cfg_meta(con: sqlite3.Connection, key: str, default: str = "") -> str:
    try:
        r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if r and r[0] is not None:
            return str(r[0])
    except Exception:
        pass
    return default


def pick_trained_chara(con: sqlite3.Connection) -> tuple[int | None, str]:
    """客户端选角色时不发请求，所以这里按策略挑一个当玩家位。

    策略优先级：
      1. meta.pick_chara_id —— 编辑器里显式指定（最可靠）
      2. meta.pick_chara_strategy = "rank" → rank_score 最高
      3. 默认 → create_time 最新的一个（刚育成的通常就是要用的）
    """
    import msgpack

    forced = _cfg_meta(con, "pick_chara_id", "").strip()
    if forced.isdigit():
        return int(forced), f"meta.pick_chara_id={forced}"

    r = con.execute("SELECT data FROM response_cache WHERE path='load/index'").fetchone()
    if not r:
        return None, "无 load/index 模板"
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    arr = (obj.get("data") or {}).get("trained_chara_array") or []
    if not arr:
        return None, "trained_chara_array 为空"

    strat = _cfg_meta(con, "pick_chara_strategy", "recent").strip().lower()
    if strat == "rank":
        best = max(arr, key=lambda x: int(x.get("rank_score") or 0))
        tid = best.get("trained_chara_id")
        return tid, f"策略=rank 选了 trained_chara_id={tid}（rank_score={best.get('rank_score')}）"

    # 默认：create_time 最新
    with_t = [x for x in arr if x.get("create_time")]
    if not with_t:
        best = arr[0]
    else:
        best = max(with_t, key=lambda x: str(x.get("create_time")))
    tid = best.get("trained_chara_id")
    return tid, (f"策略=recent 选了 trained_chara_id={tid}"
                 f"（create_time={best.get('create_time')} card={best.get('card_id')}）")


def build_race_entry(con: sqlite3.Connection, trained_chara_id: int | None,
                     ultimate_race_id: int | None = None):
    """返回 (data_dict, note_str)。失败时返回 (None, reason)。

    【关键】返回前把 race_horse_data_array 按 frame_order 排序。
    原因：
      - 帧数据（race_scenario）里每匹马的 LanePosition 严格递增（0, 555, 1111, ...），
        是「第几个位置」的均匀分配，对应 frame_order 顺序。
      - 结果块也按同一顺序排（实测模板里块 N 对应 frame_order N+1）。
      - 但 race_entry 原始数组顺序是乱的（玩家在 idx 0、frame_order=4）。
    重排后：数组 idx = frame_order - 1，两边索引一致，服务器生成剧本时
    只用一个 idx 就能同时对齐帧数据和结果块。
    """
    import msgpack

    # 模板：现有缓存的 race_entry（18 匹马）
    r = con.execute("SELECT data FROM response_cache WHERE path='ultimate_race/race_entry'").fetchone()
    if not r:
        return None, "库里没有 race_entry 模板"
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    data = copy.deepcopy(obj.get("data") or {})

    if not trained_chara_id:
        # 客户端选角不发请求 → 按策略挑一个，否则会一直显示模板角色（金花，第 4 位）
        _picked, _pnote = pick_trained_chara(con)
        if not _picked:
            return data, f"无 trained_chara_id 且挑选失败（{_pnote}），用模板"
        trained_chara_id = int(_picked)
        print(f"[race_entry] {_pnote}")

    t = _find_trained(con, trained_chara_id)
    if not t:
        return data, f"trained_chara_id={trained_chara_id} 不在 load/index，用模板"

    hs = data.get("race_horse_data_array") or []
    if not hs:
        return data, "模板没有 race_horse_data_array"

    me = hs[0]
    old = (me.get("chara_id"), me.get("nickname_id"), me.get("speed"))
    filled = []

    # 名字相同的字段（含称号 nickname_id、单机角色、适性全 10 项、技能、鞍）
    for k in _SAME:
        if k in t and t[k] is not None:
            me[k] = copy.deepcopy(t[k])
            filled.append(k)

    # power → pow
    if t.get("power") is not None:
        me["pow"] = t["power"]
        filled.append("pow")

    # 名字不同的字段
    for dst, src in _MAP.items():
        if src in t and t[src] is not None:
            me[dst] = copy.deepcopy(t[src])
            filled.append(dst)

    # chara_id 由 card_id 推（card 114101 → chara 1141）
    card = t.get("card_id")
    if isinstance(card, int) and card > 0:
        me["chara_id"] = card // 100

    me["trained_chara_id"] = trained_chara_id

    # 夹到游戏合法上限
    try:
        import attr_limits
        attr_limits.clamp_horse(me)
    except Exception:
        pass

    new = (me.get("chara_id"), me.get("nickname_id"), me.get("speed"))
    npc_note = ""

    # 【传奇赛固定阵容】用 ultimate_race_npc 的原始对手替换模板里那批。
    # 依据：ultimate_race_contents → race_instance.npc_group_id → ultimate_race_npc，
    # 每组 2~3 个真实角色强敌（speed 1600~1730）+ 若干 chara_id=1 的路人（mob_id 区分）。
    # 组内记录比 entry_num 多 1（备用位），get_lineup 已按 entry_num-1 截好。
    if ultimate_race_id:
        try:
            import sys as _sys2
            if r"C:/Users/Schwarz/uma_replay" not in _sys2.path:
                _sys2.path.insert(0, r"C:/Users/Schwarz/uma_replay")
            import npc_fixed as _nf
            lineup = _nf.get_lineup(int(ultimate_race_id))
            if lineup:
                hs = [me] + lineup
                data["race_horse_data_array"] = hs
                _sp = [h["speed"] for h in lineup]
                _strong = [h["chara_id"] for h in lineup if h["chara_id"] != 1]
                npc_note = (f" 固定阵容 {len(hs)} 匹（强敌 {len(_strong)}: {_strong[:5]} / "
                            f"speed {min(_sp)}~{max(_sp)}）")
            else:
                npc_note = " 固定阵容缺失，沿用模板对手"
        except Exception as _e_nf:
            npc_note = f" 固定阵容失败({_e_nf})，沿用模板对手"

    # 【关键】按预测名次排序 race_horse_data_array，并重新分配 frame_order。
    #
    # 反编译确认：结果界面 CreateResultBoardInitDesc (0x3E787F0) 里
    #   for (i = 0; i < arr.length; i++) arr[i] = i + 1;   // 名次 = 数组下标 + 1
    # 它根本不读 FinishOrder / CurOrder / finishTime 任何名次字段。
    #
    # 但帧数据是按 frame_order 索引的（LanePosition 0/555/1111... 对应 frame_order 1/2/3...），
    # 所以只排数组不改 frame_order 会冲突：
    #   玩家在数组 idx 0，但客户端按 frame_order=4 去读帧数据 idx 3 → 读到别人的距离。
    # 因此排序后必须把 frame_order 重新分配成 1..N，让三者统一：
    #   数组 idx = frame_order - 1 = 名次 - 1
    try:
        import sys as _sys
        if r"C:/Users/Schwarz/uma_replay" not in _sys.path:
            _sys.path.insert(0, r"C:/Users/Schwarz/uma_replay")
        import gen_race_full as _grf
        hs.sort(key=lambda x: -_grf.cruise_speed(int(x.get("speed") or 1000)))
    except Exception:
        hs.sort(key=lambda x: -(x.get("speed") or 0))

    # 重新分配 frame_order（闸位）：第 1 名 → 1、第 2 名 → 2 ...
    for i, h in enumerate(hs):
        h["frame_order"] = i + 1

    # 【单变量实验】只改 popularity，写成按名次递增的 1-based 值（玩家 = 1）。
    # mark_rank 保持服务器原值不动，避免重演「三个双圈」。
    # 依据反编译：HorseData.InitPopularity 里
    #     Popularity(+0x48) = RaceHorseData.popularity(+0x80) - 1
    # 而结果列表 FUN_183DC2270 用 (+0x48 + 1) 拼「N着」文本 ——
    # 若这两个是同一字段，改名次就会跟着变；若不变，说明「N着」另有来源。
    # 所有角色（含玩家）的干劲都随机 —— 干劲同时影响人气三印记补正和速度，
    # 真实比赛里本来就是随机的，不该固定成某个值。
    try:
        import sys as _sys3
        if r"C:/Users/Schwarz/uma_replay" not in _sys3.path:
            _sys3.path.insert(0, r"C:/Users/Schwarz/uma_replay")
        import npc_gen as _ng2
        for h in hs:
            h["motivation"] = _ng2.random_motivation()
    except Exception:
        pass

    for i, h in enumerate(hs):
        h["popularity"] = i + 1

    # 【人气三印记】按 wiki 的 φ 公式实时计算，替换掉模板里的录制值。
    # 公式来源：左=φ(速度补正×φ(毅力)^0.5) 中=φ(耐力补正×φ(毅力)^0.8×φ(智力)^0.6)
    #         右=φ(力量补正×φ(智力)^0.5)
    mark_note = ""
    if ultimate_race_id:
        try:
            import sys as _sys4, json as _json4
            if r"C:/Users/Schwarz/uma_replay" not in _sys4.path:
                _sys4.path.insert(0, r"C:/Users/Schwarz/uma_replay")
            import popularity as _pop
            # 查赛道参数（distance / ground）
            _pf = r"C:/Users/Schwarz/uma_replay/race_profiles.json"
            _dist, _grd = None, 1
            try:
                _pr = _json4.loads(open(_pf, encoding="utf-8").read())
                _u = (_pr.get("ultimate") or {}).get(str(ultimate_race_id))
                if _u:
                    _c = (_pr.get("courses") or {}).get(str(_u.get("course_set"))) or {}
                    _dist = _c.get("distance")
                    _grd = _c.get("ground", 1)
            except Exception:
                pass
            if _dist:
                _mk = _pop.calc_mark_rank(hs, float(_dist), int(_grd))
                for _i, _h in enumerate(hs):
                    _h["popularity_mark_rank_array"] = _mk[_i]
                _top = sum(1 for m in _mk if m[0] == 1)
                mark_note = f" 印记已按 φ 公式算（{_dist:.0f}m ground={_grd}，左列首位 {_top} 个）"
        except Exception as _e_mk:
            mark_note = f" 印记计算失败({_e_mk})"

    return data, (f"马0: {old} → {new}（trained={trained_chara_id}, "
                  f"替换 {len(filled)} 个字段{npc_note}{mark_note}, 按预测名次排序 + 重排 frame_order）")
