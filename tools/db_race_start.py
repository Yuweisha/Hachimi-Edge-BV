"""按客户端传入的 trained_chara_id，动态生成 ultimate_race/race_start 的 race_scenario。

流程：
    race_start 请求 {running_style, is_short}
      → 从 load/index 的 trained_chara 里查属性（用最近的 race_entry 请求里的 trained_chara_id）
      → 用模板剧本 + 属性算轨迹
      → 返回新剧本

用法（服务器内部调用）：
    from db_race_start import build_race_start
    data, note = build_race_start(con, trained_chara_id, req)
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def _gen_mod():
    """导入生成器（gen_race_full.py 在 uma_replay 下）。"""
    import importlib

    p = Path(r"C:/Users/Schwarz/uma_replay")
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    import gen_race_full

    return importlib.reload(gen_race_full)


def _find_trained(con: sqlite3.Connection, trained_chara_id: int):
    import msgpack

    r = con.execute("SELECT data FROM response_cache WHERE path='load/index'").fetchone()
    if not r:
        return None
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    for t in (obj.get("data") or {}).get("trained_chara") or []:
        if t.get("trained_chara_id") == trained_chara_id:
            return t
    return None


def _race_horses(con: sqlite3.Connection):
    """从 race_entry 拿 17 匹马的属性，返回 [{idx, speed, stamina, trained_chara_id}, ...]。

    【关键】idx 是 **数组位置**（0-based），不是 frame_order-1。
    实测依据：
      - race_scenario 帧数据里每匹马的 LanePosition 严格递增（0, 555, 1111, ...），
        说明帧数据按 race_horse_data_array 的数组顺序排，不按 frame_order 排。
      - 结果块也按同一顺序排。
      - 客户端 RaceSimulateData.GetDistance/GetResult 用同一个 horseIndex 索引两者，
        而 horseIndex 就是数组下标。
    frame_order 只是闸位（起跑位置），和数组下标无关。玩家通常在数组 idx=0。
    """
    import msgpack

    r = con.execute(
        "SELECT data FROM response_cache WHERE path='ultimate_race/race_entry'").fetchone()
    if not r:
        return []
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    hs = (obj.get("data") or {}).get("race_horse_data_array") or []
    out = []
    for arr_idx, h in enumerate(hs):
        out.append({
            "idx": arr_idx,
            "speed": int(h.get("speed") or 1000),
            "stamina": int(h.get("stamina") or 1000),
            "power": int(h.get("pow") or 1000),
            "guts": int(h.get("guts") or 1000),
            "wiz": int(h.get("wiz") or 1000),
            # 跑法是客户端在 race_start 里通知的（玩家那匹），NPC 沿用 race_entry 下发的值
            "running_style": int(h.get("running_style") or 0),
            "motivation": int(h.get("motivation") or 3),
            "trained_chara_id": h.get("trained_chara_id"),
            "frame_order": h.get("frame_order"),
            "chara_id": h.get("chara_id"),
            "viewer_id": h.get("viewer_id"),
        })
    return out


def _player_pos(con: sqlite3.Connection) -> int:
    """玩家在排序后数组里的位置（= 预测名次 - 1）。

    必须用和 build_race_start / db_race_entry 完全相同的排序
    （cruise_speed(speed) 降序），否则 idx 和客户端看到的马错位。
    """
    hs = _race_horses(con)
    if not hs:
        return 0
    try:
        import sys as _sys
        if r"C:/Users/Schwarz/uma_replay" not in _sys.path:
            _sys.path.insert(0, r"C:/Users/Schwarz/uma_replay")
        import gen_race_full as _grf
        hs.sort(key=lambda x: -_grf.cruise_speed(int(x.get("speed") or 1000)))
    except Exception:
        hs.sort(key=lambda x: -(x.get("speed") or 0))
    for i, h in enumerate(hs):
        vid = h.get("viewer_id")
        if vid and vid != 0:
            return i
    best_i, best_v = 0, -1
    for i, h in enumerate(hs):
        v = h.get("trained_chara_id") or 0
        if v > best_v:
            best_i, best_v = i, v
    return best_i


def use_real_model(con) -> bool:
    """是否启用真实解包模型生成剧本（编辑器「服务器」页的开关）。

    权威在数据库 meta.use_real_model —— 与 mode 一样，改文件已废弃。
    默认 False（走模板），只有显式设成 1 才从零生成。
    """
    try:
        r = con.execute("SELECT value FROM meta WHERE key='use_real_model'").fetchone()
        return bool(r and str(r[0]) == "1")
    except Exception:
        return False


def build_race_start(con: sqlite3.Connection, trained_chara_id: int | None, req: dict | None):
    """返回 (race_scenario_bytes, note_str)。失败返回 (None, reason)。"""
    import base64
    import gzip
    import msgpack

    r = con.execute("SELECT data FROM response_cache WHERE path='ultimate_race/race_start'").fetchone()
    if not r:
        return None, "库里没有 race_start 模板"
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    data = obj.get("data") or {}
    enc = data.get("race_scenario")
    if not enc:
        return None, "模板缺 race_scenario"

    tpl = gzip.decompress(base64.b64decode(enc))

    # 【诊断开关】passthrough.txt 存在时，原样返回模板剧本（不生成）。
    # 用来验证「原始数据在客户端跑出来是几着」。
    from pathlib import Path as _Pth
    if _Pth(r"C:/Users/Schwarz/uma_replay/passthrough.txt").exists():
        return tpl, "PASSTHROUGH：原样返回模板（未生成）"

    t = _gen_mod().parse(tpl)
    nh = t["nh"]

    # ---- 17 匹全量属性（关键：不能只算玩家）----
    horses = _race_horses(con)
    if not horses:
        return None, "race_entry 里没有马数据"
    # race_entry 返回前会按 cruise_speed(speed) 排序并重排 frame_order，
    # 但 DB 里存的还是旧顺序。这里必须用同一套排序，否则 speeds[i]
    # 和客户端看到的马对不上（表现：画面里两匹马重叠、名次全乱）。
    try:
        import sys as _sys
        if r"C:/Users/Schwarz/uma_replay" not in _sys.path:
            _sys.path.insert(0, r"C:/Users/Schwarz/uma_replay")
        import gen_race_full as _grf
        horses.sort(key=lambda x: -_grf.cruise_speed(int(x.get("speed") or 1000)))
    except Exception:
        horses.sort(key=lambda x: -(x.get("speed") or 0))
    for i, h in enumerate(horses):
        h["idx"] = i

    speeds = [1000] * nh
    stams = [1000] * nh
    for h in horses:
        i = h["idx"]
        if 0 <= i < nh:
            speeds[i] = h["speed"]
            stams[i] = h["stamina"]

    mypos = _player_pos(con)
    if not (0 <= mypos < nh):
        mypos = 0

    import struct as _st

    # ---- 赛道参数：优先用 race_entry 记下的 ultimate_race_id 查 master 表 ----
    # race_start 请求里没有赛道 ID，只能靠上一跳 race_entry 的上下文。
    # 链路：ultimate_race_id → race_instance_id → race_id → course_set
    #       → distance / finish_time_min / finish_time_max
    distance = None
    t_ref = None
    ctx_nh = None
    _prof_path = r"C:/Users/Schwarz/uma_replay/race_profiles.json"
    _ctx_path = r"C:/Users/Schwarz/uma_replay/last_race_ctx.json"
    try:
        import json as _json, time as _time, os as _os
        if _os.path.exists(_ctx_path) and _os.path.exists(_prof_path):
            with open(_ctx_path, encoding="utf-8") as _f:
                _ctx = _json.load(_f)
            age = _time.time() - float(_ctx.get("ts") or 0)
            _uid = _ctx.get("ultimate_race_id")
            if age < 300 and isinstance(_ctx.get("nh"), int) and _ctx["nh"] > 0:
                ctx_nh = int(_ctx["nh"])
            # 上下文超过 5 分钟视为过期（防止拿上一局的赛道）
            if _uid is not None and age < 300:
                with open(_prof_path, encoding="utf-8") as _f:
                    _prof = _json.load(_f)
                _u = _prof["ultimate"].get(str(_uid))
                if _u:
                    _c = _prof["courses"].get(str(_u["course_set"]))
                    if _c:
                        distance = float(_c["distance"])
                        t_ref = float(_c["t_max"])
    except Exception as _e_prof:
        pass

    if distance is None:
        # 回退：模板最后一帧跑得最远的那匹 = 赛道长度
        try:
            cs, nf, fb = t["cs"], t["nf"], t["fb"]
            base_off = 32 + (nf - 1) * fb + 4
            mx = 0.0
            for k in range(nh):
                d0 = _st.unpack_from("<f", tpl, base_off + k * cs)[0]
                if d0 > mx:
                    mx = d0
            distance = mx if mx > 100 else 3200.0
        except Exception:
            distance = 3200.0

    # player_pos=None → 17 匹全部按属性重算。
    # 只算玩家会导致「玩家冲线后继续跑、NPC 冻结在模板最后一帧」，名次会反超。
    #
    # rank_gap：按名次给速度分级，强制拉开冲线时间。
    # 属性驱动的 cruise_speed(attr) 用 speed^0.066，17 匹速度差不到 1%，
    # 全部挤在同一帧冲线（帧间隔 0.86s），名次只能由客户端 tie-break 决定 → 不可控。
    # 0.15 → 第 1 名比最后一名快 15%，每名约 1.2s 差距，大于一帧，名次锁定为数组顺序。
    # 【按实际值】速度完全由属性决定，不再叠加人为的名次系数。
    # race_entry 的 speed 从 2287 到 1181，经 cruise_speed = K×speed^0.066
    # 已产生约 6.5% 的速度差，对应 3200m 上十几秒的真实差距。
    # 再加 rank_gap 会双重放大（实测 0.03 时全场差 18.65 秒）。
    # 只保留 0.004 的极小值，用于属性完全相同的马之间打破并列。
    RANK_GAP = 0.004

    # 跑法：玩家那匹用 race_start 请求里通知的 running_style，
    # NPC 用 race_entry 下发的原值。数组顺序与 build_race_start 的排序一致。
    _styles = [2] * nh
    for h in horses:
        i = h["idx"]
        if 0 <= i < nh:
            _styles[i] = int(h.get("running_style") or 2)
    # req 可能是 dict（历史请求）或 int（当前请求体里直接取出的 running_style）
    if isinstance(req, dict):
        _req_style = req.get("running_style")
    elif isinstance(req, int):
        _req_style = req
    else:
        _req_style = None
    if _req_style and 0 <= mypos < nh:
        _styles[mypos] = int(_req_style)

    # 【完全从零生成】scratch.txt 存在时不使用任何模板字节，
    # Header / 帧区 / lens / 结果块 / 尾部全部按反编译出的布局自行构造。
    from pathlib import Path as _Pth
    # 安全阀：拿不到真实赛道参数（ctx 缺失/过期/查表失败）时绝不从零生成，
    # 否则会用模板距离（3285m）去跑一张 1600m 的赛道，客户端直接卡在赛前画面。
    _src_horses = horses          # 已排序、含全部属性字段
    _ground_cond = None
    _weather_cond = None
    try:
        import json as _jsong
        with open(r"C:/Users/Schwarz/uma_replay/last_race_ctx.json", encoding="utf-8") as _fg:
            _gctx = _jsong.load(_fg)
        _ground_cond = _gctx.get("ground_condition")
        _weather_cond = _gctx.get("weather")
    except Exception:
        pass
    if use_real_model(con) and t_ref:
        # 【关键】马数必须跟 race_entry 实际返回的一致（传奇赛按赛事固定 14/17 匹），
        # 不能沿用模板的 17 —— 否则客户端按 14 匹加载、剧本却是 17 匹，直接卡住。
        if ctx_nh:
            nh = ctx_nh
        elif horses:
            nh = len(horses)
        speeds = (speeds + [1000] * nh)[:nh]
        stams = (stams + [1000] * nh)[:nh]
        _styles = (_styles + [2] * nh)[:nh]
        # 真实解包模型（race_sim_real + gen_race_real）
        _grade = {8: "S", 7: "A", 6: "B", 5: "C", 4: "D", 3: "E", 2: "F", 1: "G"}
        def _g(v, default="A"):
            try:
                return _grade.get(int(v), default)
            except Exception:
                return default
        _horses = []
        for _i in range(nh):
            _h = _src_horses[_i] if _i < len(_src_horses) else {}
            _horses.append({
                "speed": int(_h.get("speed") or 1000),
                "stamina": int(_h.get("stamina") or 1000),
                "power": int(_h.get("power") or 1000),
                "guts": int(_h.get("guts") or 1000),
                "wiz": int(_h.get("wiz") or 1000),
                "motivation": int(_h.get("motivation") or 3),
                # 玩家那匹必须用请求里的 running_style（_styles 已被覆盖），
                # NPC 才用自己的 running_style。之前把 _h 放前面，导致选跑法完全无效。
                "style": (int(_styles[_i]) if _i == mypos
                          else int(_h.get("running_style") or _styles[_i] or 2)),
                "proper_distance_short": _g(_h.get("proper_distance_short")),
                "proper_distance_mile": _g(_h.get("proper_distance_mile")),
                "proper_distance_middle": _g(_h.get("proper_distance_middle")),
                "proper_distance_long": _g(_h.get("proper_distance_long")),
                "proper_ground_turf": _g(_h.get("proper_ground_turf")),
                "proper_ground_dirt": _g(_h.get("proper_ground_dirt")),
                "proper_running_style_nige": _g(_h.get("proper_running_style_nige")),
                "proper_running_style_senko": _g(_h.get("proper_running_style_senko")),
                "proper_running_style_sashi": _g(_h.get("proper_running_style_sashi")),
                "proper_running_style_oikomi": _g(_h.get("proper_running_style_oikomi")),
            })
        import sys as _sysR
        if r"C:/Users/Schwarz/uma_replay" not in _sysR.path:
            _sysR.path.insert(0, r"C:/Users/Schwarz/uma_replay")
        import gen_race_real as _grr
        # 场地：race_instance 的 ground（1 草地 / 2 泥地），缺失按草地
        _ground = int(_ground_cond or 1)
        _cond = int(_weather_cond or 1)
        out = _grr.build_real(_horses, float(distance), _ground, _cond,
                              t_ref=t_ref, seed=None)
        _v, _s, _sd, _n, _c, _k, _nf, _fb = _st.unpack_from("<8I", out, 0)
        note = (f"trained={trained_chara_id} pos={mypos} "
                f"style={_req_style if _req_style is not None else '?'} "
                f"→ SCRATCH 从零生成 {len(out):,} B（{distance:.0f} m / t_ref={t_ref or 0:.1f}s / "
                f"{_nf} 帧 / nh={_n} cs={_c} fb={_fb}）")
        return out, note

    out = _gen_mod().build(tpl, speeds, stams, distance, player_pos=None, rank_gap=RANK_GAP)


    me = {h["idx"]: h for h in horses}.get(mypos, {})
    style = _req_style if _req_style is not None else "?"
    fname = Path(__file__).name
    note = (f"trained={trained_chara_id} pos={mypos} style={style} "
            f"speed={me.get('speed', me.get('speed'))} sta={me.get('stamina', me.get('stamina'))} "
            f"→ 全量 {nh} 马重算 {len(out):,} B（{distance:.0f} m）")
    return out, note
