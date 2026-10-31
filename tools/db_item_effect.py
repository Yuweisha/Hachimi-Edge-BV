"""传奇赛赛前道具效果（reflect_item_effect）。

接口行为（实测）：
    请求  {item_id_array: [116, 119]}
    响应  {weather, ground_condition, race_horse_data_array, item_info_array, state}
即「给道具 ID 列表 → 返回应用后的马数据与天气」，剧本不用重算。

道具效果语义（item_data，item_category=150 是传奇赛专用）：
    effect_type  含义
      10         干劲，effect_value = 目标干劲（1~5）
      20         天气，1晴 2阴 3雨 4雪
      30         马场状态，1良 2重 3稍重 4不良
      40         枠番（闸位）调整，target=1 内枠 / target=2 外枠
       2         体力（食物类，非赛前道具，传奇赛用不到）

天气与马场对速度的影响：master.mdb 里没有这张表（race_condition.rate 是
「该天气出现的概率」，不是速度系数）。客户端也不读这两个字段改变跑动，
所以系数由服务器自己定，用于调整 t_ref（时长放大 = 速度缩小）。
"""
import copy
import sqlite3

MDB = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb"

# 马场状态：1良 2重 3稍重 4不良
GROUND_MUL = {1: 1.000, 2: 0.975, 3: 0.985, 4: 0.965}
# 天气：1晴 2阴 3雨 4雪
WEATHER_MUL = {1: 1.000, 2: 1.000, 3: 0.995, 4: 0.980}


def weather_ground_mul(weather: int, ground: int) -> float:
    """天气 × 马场 的速度乘数（<1 表示变慢）。"""
    return GROUND_MUL.get(int(ground or 1), 1.0) * WEATHER_MUL.get(int(weather or 1), 1.0)


def _item_effects(item_id: int) -> list:
    """返回 [(effect_type, effect_target, effect_value), ...]"""
    try:
        con = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        row = con.execute("""
            SELECT effect_type_1, effect_target_1, effect_value_1,
                   effect_type_2, effect_target_2, effect_value_2
            FROM item_data WHERE id = ?
        """, (int(item_id),)).fetchone()
        con.close()
    except Exception:
        return []
    if not row:
        return []
    out = []
    for t, tg, v in ((row[0], row[1], row[2]), (row[3], row[4], row[5])):
        if t:
            out.append((int(t), int(tg), int(v)))
    return out


def apply_reflect_item_effect(con: sqlite3.Connection, req: dict | None):
    """返回 (data_dict, note)。失败返回 (None, reason)。

    req = {"item_id_array": [...], "trained_chara_id"?: ...}
    """
    import msgpack
    req = req or {}
    item_ids = [int(x) for x in (req.get("item_id_array") or []) if x]

    r = con.execute(
        "SELECT data FROM response_cache WHERE path='ultimate_race/reflect_item_effect'").fetchone()
    if not r:
        return None, "库里没有 reflect_item_effect 模板"
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    data = copy.deepcopy(obj.get("data") or {})
    hs = data.get("race_horse_data_array") or []
    if not hs:
        return None, "模板缺 race_horse_data_array"

    weather = int(data.get("weather") or 1)
    ground = int(data.get("ground_condition") or 1)

    # 玩家 = viewer_id 非 0 的那匹
    my_idx = next((i for i, h in enumerate(hs) if h.get("viewer_id")), 0)

    applied = []
    _seen = set()
    for iid in item_ids:
        for etype, etarget, evalue in _item_effects(iid):
            # item_data 的 type_1 / type_2 可能是同一效果的重复描述
            # （如干劲UPスイーツ两个字段都是 type=10 value=4），按 (type,target) 去重
            if (etype, etarget) in _seen:
                continue
            _seen.add((etype, etarget))
            if etype == 10:
                # 干劲：直接设成目标值
                for h in hs:
                    if h is hs[my_idx]:
                        h["motivation"] = max(1, min(5, evalue))
                applied.append(f"干劲⟶{evalue}")
            elif etype == 20:
                weather = evalue
                applied.append(f"天气={evalue}")
            elif etype == 30:
                ground = evalue
                applied.append(f"马场={evalue}")
            elif etype == 40:
                # 枠番：内枠把玩家往前排，外枠往后排
                if 0 <= my_idx < len(hs):
                    n = len(hs)
                    if etarget == 1:
                        want = max(1, min(n, evalue))
                    else:
                        want = max(1, min(n, n - evalue + 1))
                    hs[my_idx]["frame_order"] = want
                    applied.append(f"枠番⟶{want}")
            elif etype == 2:
                # 食物类：加体力（这里落到 stamina，传奇赛本身无体力概念）
                hs[my_idx]["stamina"] = int(hs[my_idx].get("stamina") or 1000) + evalue
                applied.append(f"耐力+{evalue}")

    data["weather"] = weather
    data["ground_condition"] = ground
    data["race_horse_data_array"] = hs
    # 道具剩余数量沿用模板（真实库存扣减不在本接口处理）
    if not data.get("item_info_array"):
        data["item_info_array"] = [{"item_id": iid, "number": 1} for iid in item_ids]

    mul = weather_ground_mul(weather, ground)
    note = (f"道具 {item_ids or '无'} → {' / '.join(applied) if applied else '无变化'}；"
            f"天气={weather} 马场={ground} 速度×{mul:.4f}")
    return data, note


if __name__ == "__main__":
    con = sqlite3.connect(r"C:/Users/Schwarz/uma_replay/offline.db")
    for ids in ([], [116], [117], [118], [119], [120], [116, 117, 119]):
        d, note = apply_reflect_item_effect(con, {"item_id_array": ids})
        print(f"{str(ids or '空'):<18} {note}")
    con.close()
