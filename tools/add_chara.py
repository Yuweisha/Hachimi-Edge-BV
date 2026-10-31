"""往 offline.db 里添加一匹合法的育成角色。

必须同步 5 处，漏一处客户端就读不出来（殿堂会报"无法读取数据"）：
  1. load/index.trained_chara                主表，53 字段
  2. load/index.chara_list[chara_id]         max_grade / training_num / fan / love_point
  3. note/index.top_directory_card_array     殿堂 42 条，嵌套完整记录
  4. note/get_directory_card.directory_card_array  殿堂 12 条
  5. trained_chara_favorite_array（可选）

用法：
    python add_chara.py --card 111401 --speed 2287 --stamina 1362 --power 1704 \
        --guts 1290 --wiz 1412 --rank-score 61423 --rank 86 --skill 101141,200011,...
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sqlite3
import time
from pathlib import Path

import msgpack

BASE = Path(r"C:/Users/Schwarz/uma_replay")
DB = BASE / "offline.db"

# rank_score → rank 的分段（从 90 匹实测反推，单调递增，允许跳号）
RANK_TABLE = [
    (16176, 16), (21707, 24), (22926, 26), (29008, 39), (30233, 41),
    (32368, 45), (32813, 46), (34605, 49), (35084, 50), (35946, 51),
    (36582, 52), (37267, 53), (37523, 54), (38431, 55), (39024, 56),
    (39734, 57), (40521, 58), (42392, 61), (43259, 62), (43489, 63),
    (44396, 64), (44744, 65), (45406, 66), (46206, 67), (46923, 68),
    (48466, 70), (49128, 71), (51960, 74), (52821, 76), (53770, 77),
    (54412, 78), (61423, 86),
]

MAX_ATTR = {"speed": 2287, "stamina": 1850, "power": 1825, "wiz": 1815, "guts": 1700}

# ---- 评分公式（移植自 wiki.biligame.com 评分计算器）----
# 五维分段系数：每 50 点一档，超 1200 后走 OVK
KOEFFI = [0.5, 0.8, 1, 1.3, 1.6, 1.8, 2.1, 2.4, 2.6, 2.8, 2.9, 3, 3.1, 3.3, 3.4,
          3.5, 3.9, 4.1, 4.2, 4.3, 5.2, 5.5, 6.6, 6.8, 6.9]
OVK = [7.888, 8, 8.1, 8.3, 8.4, 8.5, 8.6, 8.8, 8.9, 9, 9.2, 9.3, 9.4, 9.6, 9.7, 9.8,
       10, 10.1, 10.2, 10.3, 10.5, 10.6, 10.7, 10.9, 11, 11.1, 11.3, 11.4, 11.5, 11.7,
       11.8, 11.9, 12.1, 12.2, 12.3, 12.4, 12.6, 12.7, 12.8, 13, 13.1, 13.2, 13.4, 13.5,
       13.6, 13.8, 13.9, 14, 14.1, 14.3, 14.4, 14.5, 14.7, 14.8, 14.9, 15.1, 15.2, 15.3,
       15.5, 15.6, 15.7, 15.9, 16, 16.1, 16.2, 16.4, 16.5, 16.6, 16.8, 16.9, 17, 17.2,
       17.3, 17.4, 17.6, 17.7, 17.8, 17.9, 18.1, 18.2, 18.3]

# 评级阈值（从 G+ 到 LF，共 123 档，来自 wiki 计算器）
GRADE_TABLE = [
    (91400, "LF"), (90900, "LG24"), (90300, "LG23"), (89700, "LG22"), (89100, "LG21"),
    (88500, "LG20"), (87900, "LG19"), (87300, "LG18"), (86700, "LG17"), (86200, "LG16"),
    (85600, "LG15"), (84900, "LG14"), (84300, "LG13"), (83600, "LG12"), (83000, "LG11"),
    (82300, "LG10"), (81700, "LG9"), (81000, "LG8"), (80400, "LG7"), (79700, "LG6"),
    (79100, "LG5"), (78500, "LG4"), (77800, "LG3"), (77200, "LG2"), (76600, "LG1"),
    (76000, "LG"), (74400, "US9"), (72900, "US8"), (71600, "US7"), (70300, "US6"),
    (69000, "US5"), (67700, "US4"), (66400, "US3"), (65100, "US2"), (64200, "US1"),
    (63400, "US"), (62500, "UA9"), (61700, "UA8"), (60800, "UA7"), (60000, "UA6"),
    (59200, "UA5"), (58400, "UA4"), (57500, "UA3"), (56700, "UA2"), (55900, "UA1"),
    (55200, "UA"), (54400, "UB9"), (53600, "UB8"), (52800, "UB7"), (52000, "UB6"),
    (51300, "UB5"), (50500, "UB4"), (49800, "UB3"), (49000, "UB2"), (48300, "UB1"),
    (47600, "UB"), (46900, "UC9"), (46200, "UC8"), (45400, "UC7"), (44700, "UC6"),
    (44000, "UC5"), (43400, "UC4"), (42700, "UC3"), (42000, "UC2"), (41300, "UC1"),
    (40700, "UC"), (40000, "UD9"), (39400, "UD8"), (38700, "UD7"), (38100, "UD6"),
    (37500, "UD5"), (36800, "UD4"), (36200, "UD3"), (35600, "UD2"), (35000, "UD1"),
    (34400, "UD"), (33800, "UE9"), (33200, "UE8"), (32700, "UE7"), (32100, "UE6"),
    (31500, "UE5"), (31000, "UE4"), (30400, "UE3"), (29900, "UE2"), (29400, "UE1"),
    (28800, "UE"), (28300, "UF9"), (27800, "UF8"), (27300, "UF7"), (26800, "UF6"),
    (26300, "UF5"), (25800, "UF4"), (25300, "UF3"), (24800, "UF2"), (24300, "UF1"),
    (23900, "UF"), (23400, "UG9"), (23000, "UG8"), (22500, "UG7"), (22100, "UG6"),
    (21600, "UG5"), (21200, "UG4"), (20800, "UG3"), (20400, "UG2"), (20000, "UG1"),
    (19600, "UG"), (19200, "SS+"), (17500, "SS"), (15900, "S+"), (14500, "S"),
    (12100, "A+"), (10000, "A"), (8200, "B+"), (6500, "B"), (4900, "C+"),
    (3500, "C"), (2900, "D+"), (2300, "D"), (1800, "E+"), (1300, "E"),
    (900, "F+"), (600, "F"), (300, "G+"),
]

# 评级 → 游戏内 rank 数字（从 90 匹实测记录反推；高端按序补）
GRADE_TO_RANK = {
    "LF": 110,
    "LG24": 109, "LG23": 108, "LG22": 107, "LG21": 106, "LG20": 105,
    "LG19": 104, "LG18": 103, "LG17": 102, "LG16": 101, "LG15": 100,
    "LG14": 99, "LG13": 98, "LG12": 97, "LG11": 96, "LG10": 95,
    "LG9": 94, "LG8": 93, "LG7": 92, "LG6": 91, "LG5": 91,
    "LG4": 90, "LG3": 90, "LG2": 89, "LG1": 89, "LG": 89,
    "US9": 88, "US8": 88, "US7": 87, "US6": 87, "US5": 87,
    "US4": 87, "US3": 86, "US2": 86, "US1": 86, "US": 85,
    "UA6": 86, "UA7": 85, "UA8": 87, "UA9": 88,
    "UB7": 78, "UB6": 76, "UB5": 76, "UB4": 74, "UB3": 73, "UB2": 71,
    "UB1": 71, "UB": 70, "UC9": 70, "UC8": 68, "UC7": 68, "UC6": 67,
    "UC5": 66, "UC4": 65, "UC3": 63, "UC2": 62, "UC1": 61,
    "UD6": 56, "UD5": 56, "UD4": 55, "UD3": 53, "UD2": 52, "UD1": 52, "UD": 51,
    "UE9": 50, "UE8": 49, "UE7": 48, "UE5": 45, "UE1": 41,
    "UF8": 39, "UG6": 26, "UG3": 24,
}


def wuwei(value: float) -> int:
    """五维单项评分（wiki 原函数）。"""
    oval = 0.0
    if value > 1200:
        oval = value - 1200
        value = 1200
    result = 0.0
    value += 1
    q = int(value // 50)
    r = value % 50
    i = 0
    for i in range(q):
        result += 50 * KOEFFI[min(i, len(KOEFFI) - 1)]
    result += r * KOEFFI[min(i, len(KOEFFI) - 1)]
    if oval > 0:
        if oval < 9:
            ovq = int(oval // 10)
            ovr = oval % 10
            j = 0
            for j in range(ovq):
                result += 10 * OVK[min(j, len(OVK) - 1)]
            result += ovr * OVK[min(j, len(OVK) - 1)]
        else:
            result = 3912.0
            oval += 1
            ovq = int(oval // 10)
            ovr = oval % 10
            j = 0
            for j in range(1, ovq):
                result += math.ceil(10 * OVK[min(j, len(OVK) - 1)])
            result += math.ceil(ovr * OVK[min(j, len(OVK) - 1)])
    return int(math.floor(result))


def grade_of(score: int) -> str:
    for th, name in GRADE_TABLE:
        if score >= th:
            return name
    return "G"


MASTER = Path(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/"
              r"UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb")


def grade_values() -> dict[int, int]:
    """从 master 读技能的 grade_value（评价点）。"""
    try:
        mc = sqlite3.connect(f"file:{MASTER}?mode=ro", uri=True)
        d = dict(mc.execute("SELECT id, grade_value FROM skill_data").fetchall())
        mc.close()
        return d
    except Exception:
        return {}


def calc_rank_score(speed, stamina, power, guts, wiz, skill_ids) -> int:
    """wiki 公式：五维分段分 + 技能 grade_value 之和。

    实测比游戏内 rank_score 系统性低 600~1400（缺星级系数/继承技加成），
    这里按 800 中位数补上。
    """
    gv = grade_values()
    five = sum(wuwei(v) for v in (speed, stamina, power, guts, wiz))
    sk = sum(gv.get(int(s), 0) for s in skill_ids)
    return max(0, int(five + sk + 800))


def rank_from_score(score: int) -> int:
    """优先用实测 score→rank 分段表（更准），超出范围才回落到评级映射。"""
    r = 1
    for lo, rk in RANK_TABLE:
        if score >= lo:
            r = rk
        else:
            break
    if score > RANK_TABLE[-1][0]:
        g = grade_of(score)
        if g in GRADE_TO_RANK:
            return GRADE_TO_RANK[g]
    return r


def nid(con):
    return lambda p: con.execute(
        "SELECT data FROM response_cache WHERE path=?", (p,)).fetchone()[0]


def load(con, path):
    raw = nid(con)(path)
    return msgpack.unpackb(raw, raw=False, strict_map_key=False, unicode_errors="replace")


def dump(con, path, obj):
    blob = msgpack.packb(obj, use_bin_type=True)
    con.execute("UPDATE response_cache SET data=?, declared=? WHERE path=?",
                (blob, len(blob), path))
    con.execute("DELETE FROM path_declared WHERE path=?", (path,))
    con.execute("INSERT INTO path_declared(path, declared) VALUES(?,?)", (path, len(blob)))
    return len(blob)


def build_chara(con, args):
    """按模板造一条新的 trained_chara 记录。"""
    li = load(con, "load/index")
    tc = li["data"]["trained_chara"]
    by_id = {t["trained_chara_id"]: t for t in tc}

    tpl_id = args.template
    if tpl_id not in by_id:
        raise SystemExit(f"模板 trained_chara_id={tpl_id} 不存在")
    tpl = by_id[tpl_id]
    new = copy.deepcopy(tpl)

    # 递增 id
    new_tid = max(by_id) + 1
    new_smc = max(t.get("single_mode_chara_id") or 0 for t in tc) + 1
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    new["trained_chara_id"] = new_tid
    new["single_mode_chara_id"] = new_smc
    new["card_id"] = args.card
    new["chara_seed"] = args.seed
    new["create_time"] = now
    new["register_time"] = now
    new["speed"] = min(args.speed, MAX_ATTR["speed"])
    new["stamina"] = min(args.stamina, MAX_ATTR["stamina"])
    new["power"] = min(args.power, MAX_ATTR["power"])
    new["guts"] = min(args.guts, MAX_ATTR["guts"])
    new["wiz"] = min(args.wiz, MAX_ATTR["wiz"])
    new["total_skill_pt"] = args.skill_pt

    # 技能：首项必须是固有技能
    skills = [int(x) for x in args.skill.split(",") if x.strip()]
    if skills:
        new["skill_array"] = [{"skill_id": s, "level": 6 if i == 0 else 1}
                              for i, s in enumerate(skills)]

    # rank_score：传 0 就按公式自动算
    if args.rank_score:
        new["rank_score"] = args.rank_score
    else:
        new["rank_score"] = calc_rank_score(
            new["speed"], new["stamina"], new["power"], new["guts"], new["wiz"], skills)
    new["rank"] = args.rank if args.rank else rank_from_score(new["rank_score"])
    new["nickname_id"] = args.nickname
    new["nickname_id_array"] = [{"nickname_id": args.nickname}] if args.nickname else []
    new["running_style"] = args.style

    # 战绩：按胜场数造
    if args.wins > 0:
        res = []
        for i in range(args.wins):
            res.append({"turn": (i % 24) + 1, "program_id": 1000 + i,
                        "weather": 3, "ground_condition": 4, "running_style": args.style,
                        "popularity": 1, "result_rank": 1,
                        "result_time": 1170000, "prize_money": 0})
        new["race_result_list"] = res
        new["wins"] = args.wins
    new["fans"] = args.fans

    # 因子留空（服务器对未完成育成的记录就是这样）
    if args.empty_factor:
        new["factor_info_array"] = [{"factor_id": 301, "level": 0}]
        new["factor_extend_array"] = []

    return li, new


def trim_nested(nt: dict, ranking) -> dict:
    """把完整 trained_chara 裁成殿堂嵌套格式（实测：49 字段 + directory_ranking）。

    完整记录比嵌套多 5 个字段，多一个客户端就解析失败、殿堂报「无法加载数据」。
    """
    drop = {"arrive_route_race_id", "chara_seed", "register_time", "use_type", "wins"}
    out = {k: v for k, v in nt.items() if k not in drop}
    out["directory_ranking"] = ranking
    return out


def apply(con, args):
    li, new = build_chara(con, args)
    tid = new["trained_chara_id"]
    card = new["card_id"]
    chara = card // 100

    # 1) trained_chara
    li["data"]["trained_chara"].append(new)
    print(f"1. trained_chara += 1（trained_chara_id={tid}, single_mode_chara_id={new['single_mode_chara_id']}）")

    # 2) chara_list
    cl = li["data"]["chara_list"]
    entry = next((c for c in cl if c["chara_id"] == chara), None)
    if entry:
        old_g = entry["max_grade"]
        entry["max_grade"] = max(entry["max_grade"], new["rank"])
        entry["training_num"] = entry.get("training_num", 0) + 1
        entry["fan"] = entry.get("fan", 0) + new["fans"]
        entry["love_point"] = entry.get("love_point", 0) + args.love
        print(f"2. chara_list[{chara}]: max_grade {old_g}→{entry['max_grade']}, "
              f"training_num +1, fan +{new['fans']}, love +{args.love}")
    else:
        cl.append({"chara_id": chara, "training_num": 1, "love_point": args.love,
                   "fan": new["fans"], "max_grade": new["rank"],
                   "dress_id": 1, "mini_dress_id": 1, "dress_color_id": 0,
                   "mini_dress_color_id": 0, "create_time": new["create_time"],
                   "love_point_pool": 0})
        print(f"2. chara_list 新增 chara_id={chara}")

    d1 = dump(con, "load/index", li)
    print(f"   → load/index 已写，declared={d1:,}")

    # 3/4) 殿堂两张表
    for path, key, limit in (("note/index", "top_directory_card_array", 42),
                             ("note/get_directory_card", "directory_card_array", 12)):
        try:
            obj = load(con, path)
        except Exception as e:
            print(f"3/4. {path} 读取失败: {e}")
            continue
        arr = obj["data"].get(key) or []
        idx = next((i for i, x in enumerate(arr) if x.get("card_id") == card), None)
        nested = copy.deepcopy(new)
        if idx is not None:
            old = arr[idx]["trained_chara"]
            if (old.get("rank_score") or 0) >= new["rank_score"]:
                print(f"3/4. {path}: 现有记录 rank_score={old.get('rank_score')} 更高，跳过")
                continue
            arr[idx]["trained_chara"] = nested
            print(f"3/4. {path}: 替换 card {card} 的殿堂记录（ranking {arr[idx].get('directory_ranking')}）")
        else:
            if len(arr) >= limit:
                print(f"3/4. {path}: 已有 {len(arr)} 条满额，跳过")
                continue
            arr.append({"card_id": card, "directory_ranking": len(arr) + 1,
                        "trained_chara": nested})
            print(f"3/4. {path}: 新增第 {len(arr)} 条")
        obj["data"][key] = arr
        d = dump(con, path, obj)
        print(f"     → 已写，declared={d:,}")

    # 5) 收藏（可选）
    if args.favorite:
        fav = li["data"].get("trained_chara_favorite_array") or []
        fav.append({"trained_chara_id": tid, "icon_type": 0, "memo": ""})
        li["data"]["trained_chara_favorite_array"] = fav
        dump(con, "load/index", li)
        print("5. 已加入收藏")

    # 6) owned_chara 表 —— chara_list 的真正来源（load/index 里的 chara_list 是它渲染的）
    cur = con.execute(
        """UPDATE owned_chara
           SET training_num = training_num + 1,
               max_grade   = MAX(max_grade, ?),
               rank_score  = MAX(rank_score, ?),
               love_point  = love_point + ?
           WHERE chara_id = ?""",
        (new["rank"], new["rank_score"], args.love, chara))
    if cur.rowcount == 0:
        con.execute(
            """INSERT INTO owned_chara
               (chara_id, training_num, love_point, fan, max_grade, dress_id,
                mini_dress_id, dress_color_id, mini_dress_color_id, create_time,
                love_point_pool, rank_score)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (chara, 1, args.love, new["fans"], new["rank"], chara * 100 + 1,
             1, 0, 0, new["create_time"], 0, new["rank_score"]))
        print(f"6. owned_chara 新增 chara_id={chara}")
    else:
        row = con.execute(
            "SELECT training_num, max_grade, rank_score FROM owned_chara WHERE chara_id=?",
            (chara,)).fetchone()
        print(f"6. owned_chara[{chara}]: training_num={row[0]} max_grade={row[1]} "
              f"rank_score={row[2]}")

    con.commit()
    print(f"\n完成：新增 trained_chara_id={tid}（card {card}, rank {new['rank']}, "
          f"score {new['rank_score']}）")
    return tid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--template", type=int, default=604, help="复用哪条记录做模板")
    ap.add_argument("--card", type=int, required=True)
    ap.add_argument("--speed", type=int, default=1000)
    ap.add_argument("--stamina", type=int, default=1000)
    ap.add_argument("--power", type=int, default=1000)
    ap.add_argument("--guts", type=int, default=1000)
    ap.add_argument("--wiz", type=int, default=1000)
    ap.add_argument("--rank-score", type=int, default=40000)
    ap.add_argument("--rank", type=int, default=0, help="0 = 按 rank_score 自动映射")
    ap.add_argument("--skill", default="", help="逗号分隔，首项为固有技能")
    ap.add_argument("--skill-pt", type=int, default=6000)
    ap.add_argument("--wins", type=int, default=10)
    ap.add_argument("--fans", type=int, default=100000)
    ap.add_argument("--style", type=int, default=2)
    ap.add_argument("--nickname", type=int, default=378)
    ap.add_argument("--love", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--favorite", action="store_true")
    ap.add_argument("--empty-factor", action="store_true")
    a = ap.parse_args()
    if not a.seed:
        a.seed = int(time.time()) & 0x7FFFFFFF

    con = sqlite3.connect(a.db, timeout=20)
    try:
        apply(con, a)
    finally:
        con.close()


if __name__ == "__main__":
    main()
