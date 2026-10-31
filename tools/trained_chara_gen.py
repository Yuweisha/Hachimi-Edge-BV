"""往 offline.db 的 load/index 模板里添加合法的新马娘（trained_chara）。

合法性约束：
  - card_id 必须在 card_list 里存在
  - 五维不超过 MAX_ATTR
  - rank_score 用真实评分公式算，与五维自洽
  - trained_chara_id / single_mode_chara_id 递增不冲突
  - create_time 用当前时间
"""
from __future__ import annotations

import copy
import json
import random
import sqlite3
import time

# 五维上限（游戏内实际最大值）
MAX_ATTR = {"speed": 2287, "stamina": 1850, "power": 1825, "wiz": 1815, "guts": 1700}

# 评分公式系数（已逆向）
SCORE_COEF = {
    "speed": 15.7122, "stamina": 8.9403, "power": 9.0427,
    "guts": 3.5807, "wiz": 5.7326, "skill": 1.2012,
    "const": -35585.2279,
}

# rank 段位表从 master.mdb 读，避免硬编码
_RANK_TABLE = None


def _rank_table():
    global _RANK_TABLE
    if _RANK_TABLE is None:
        try:
            from rank_table import load_rank_table
            _RANK_TABLE = load_rank_table()
        except Exception:
            _RANK_TABLE = []
    return _RANK_TABLE



MASTER_MDB = (r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/"
              r"UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb")


def card_innate_skills(card_id: int, awaken_level: int = 5) -> list[dict]:
    """查 card 的固有技能（按觉醒等级过滤）。

    返回可直接放进 trained_chara.skill_array 的结构：
        [{"skill_id": 200861, "level": 1, "is_available": 1}, ...]

    真样本的 skill_array 元素结构见线上 tid=604（53 项）。
    """
    try:
        con = sqlite3.connect(f"file:{MASTER_MDB}?mode=ro", uri=True)
    except Exception:
        return []
    try:
        row = con.execute(
            "SELECT available_skill_set_id FROM card_data WHERE id=?", (card_id,)
        ).fetchone()
        if not row:
            return []
        sid = row[0]
        rows = con.execute(
            "SELECT skill_id, need_rank FROM available_skill_set "
            "WHERE available_skill_set_id=? ORDER BY need_rank, skill_id",
            (sid,),
        ).fetchall()
        return [
            {"skill_id": int(sk), "level": 1, "is_available": 1 if int(nr) <= awaken_level else 0}
            for sk, nr in rows
        ]
    except Exception:
        return []
    finally:
        con.close()


def calc_rank_score(speed: int, stamina: int, power: int, guts: int, wiz: int,
                    skill_point: int = 0) -> int:
    """按逆向公式计算评分。"""
    s = (speed * SCORE_COEF["speed"]
         + stamina * SCORE_COEF["stamina"]
         + power * SCORE_COEF["power"]
         + guts * SCORE_COEF["guts"]
         + wiz * SCORE_COEF["wiz"]
         + skill_point * SCORE_COEF["skill"]
         + SCORE_COEF["const"])
    return max(0, int(round(s)))


def rank_from_score(score: int) -> int:
    """按 master.mdb 的 single_mode_rank 反查 rank id（与评分严格自洽）。"""
    tbl = _rank_table()
    if tbl:
        for rid, lo, hi in tbl:
            if lo <= score <= hi:
                return rid
        return tbl[-1][0]
    return max(1, min(80, score // 100))


def _now_str() -> str:
    """游戏用的时间格式：YYYY-MM-DD HH:MM:SS（字符串，不是时间戳）。"""
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_template(con: sqlite3.Connection) -> dict:
    blob = con.execute("SELECT data FROM response_cache WHERE path='load/index'").fetchone()[0]
    import msgpack
    return msgpack.unpackb(blob, raw=False, strict_map_key=False)


def _save_template(con: sqlite3.Connection, obj: dict) -> int:
    """写回 load/index，并同步 trained_chara/load。

    ★ 两个接口必须一致：客户端会交叉校验，
      load/index 有而 trained_chara/load 没有 → 卡 60%。
    """
    import copy
    import msgpack

    plain = msgpack.packb(obj, use_bin_type=True)
    con.execute(
        "UPDATE response_cache SET data=?, declared=? WHERE path='load/index'",
        (plain, len(plain)),
    )

    # 同步 trained_chara/load
    row = con.execute("SELECT data FROM response_cache WHERE path='trained_chara/load'").fetchone()
    if row:
        try:
            ld = msgpack.unpackb(row[0], raw=False, strict_map_key=False)
            ld["data"]["trained_chara_array"] = copy.deepcopy(obj["data"]["trained_chara"])
            # 收藏列表过滤失效引用
            valid = {int(x["trained_chara_id"]) for x in obj["data"]["trained_chara"]}
            fav = ld["data"].get("trained_chara_favorite_array", [])
            ld["data"]["trained_chara_favorite_array"] = [
                x for x in fav if int(x.get("trained_chara_id", 0)) in valid
            ]
            lb = msgpack.packb(ld, use_bin_type=True)
            con.execute(
                "UPDATE response_cache SET data=?, declared=? WHERE path='trained_chara/load'",
                (lb, len(lb)),
            )
        except Exception:
            pass

    return len(plain)


def list_valid_cards(con: sqlite3.Connection) -> list[int]:
    """从 load/index 模板的 card_list 里取所有合法 card_id。"""
    obj = _load_template(con)
    cards = obj.get("data", {}).get("card_list", [])
    out = []
    for c in cards:
        if isinstance(c, dict) and "card_id" in c:
            out.append(int(c["card_id"]))
    return sorted(set(out))


def add_trained_chara(db_path: str, card_id: int | None = None,
                      attrs: dict | None = None,
                      seed: int | None = None,
                      rank_gain: bool = True) -> dict:
    """添加一条合法的育成完成马娘。返回新建的记录。

    args:
        card_id  卡片 ID；None 时从 card_list 随机选
        attrs    {speed,stamina,power,guts,wiz}；None 时随机生成
        seed     随机种子
    """
    rng = random.Random(seed if seed is not None else time.time_ns())
    con = sqlite3.connect(db_path)
    try:
        obj = _load_template(con)
        tc = obj.get("data", {}).get("trained_chara")
        if not isinstance(tc, list):
            raise RuntimeError("模板缺少 trained_chara")

        # 选卡片
        valid = list_valid_cards(con)
        if card_id is None:
            card_id = rng.choice(valid) if valid else 103001
        elif card_id not in valid:
            raise ValueError(f"card_id {card_id} 不在 card_list 里")

        # 五维
        if attrs is None:
            attrs = {}
            for k, cap in MAX_ATTR.items():
                lo = int(cap * 0.6)
                attrs[k] = rng.randint(lo, cap)
        else:
            for k in ("speed", "stamina", "power", "guts", "wiz"):
                if k not in attrs:
                    attrs[k] = rng.randint(600, MAX_ATTR[k])
                attrs[k] = min(int(attrs[k]), MAX_ATTR[k])

        # ID 分配
        max_id = max((int(x.get("trained_chara_id", 0)) for x in tc), default=0)
        max_sm = max((int(x.get("single_mode_chara_id", 0)) for x in tc), default=0)

        # 合法的继承引用池：只能用已存在的 trained_chara_id
        existing_ids = sorted({int(x.get("trained_chara_id", 0)) for x in tc} - {0})
        # chara_seed 必须唯一，范围参考现有（约 1e8 ~ 2.1e9）
        used_seeds = {int(x.get("chara_seed", 0)) for x in tc if x.get("chara_seed")}

        # ★ 骨架必须是「同 card_id」的记录：
        #   技能/支援卡/因子/比赛记录这些列表字段是角色专属内容，
        #   跨卡复制会让客户端校验失败（load/index 卡 60%）。
        same = [x for x in tc if int(x.get("card_id", 0)) == int(card_id)]
        if same:
            base = copy.deepcopy(same[0])
        elif tc:
            # 没有同卡记录时退回第一条，但会保留其列表（可能与 card_id 不匹配）
            base = copy.deepcopy(tc[0])
        else:
            base = {}

        # 再确认一次不越界
        for k, cap in MAX_ATTR.items():
            attrs[k] = min(int(attrs[k]), cap)

        score = calc_rank_score(
            attrs["speed"], attrs["stamina"], attrs["power"],
            attrs["guts"], attrs["wiz"], 0,
        )

        # 新 seed，避开重复
        new_seed = rng.randint(100_000_000, 2_000_000_000)
        while new_seed in used_seeds:
            new_seed = rng.randint(100_000_000, 2_000_000_000)

        # 继承引用：从已有 ID 里挑两个不同的，绝不能指向不存在的
        succ1 = succ2 = 0
        if len(existing_ids) >= 2:
            succ1, succ2 = rng.sample(existing_ids, 2)

        # 固有技能：从 master 查该卡自带的技能填进 skill_array
        innate = card_innate_skills(int(card_id), awaken_level=5)
        if innate:
            base["skill_array"] = innate

        now = int(time.time())
        base.update({
            "trained_chara_id": max_id + 1,
            "single_mode_chara_id": max_sm + 1,
            "card_id": card_id,
            "chara_seed": new_seed,
            "succession_trained_chara_id_1": succ1,
            "succession_trained_chara_id_2": succ2,
            "succession_num": 2 if succ1 and succ2 else 0,
            "speed": attrs["speed"],
            "stamina": attrs["stamina"],
            "power": attrs["power"],
            "wiz": attrs["wiz"],
            "guts": attrs["guts"],
            "rank_score": score,
            "rank": rank_from_score(score),
            "create_time": _now_str(),
            "register_time": _now_str(),
            "is_saved": 1,
            "is_locked": 0,
            "fans": rng.randint(213554, 628138),
            "rarity": 5 if attrs["speed"] > 1500 else 4,
            "talent_level": 5,
            "chara_grade": rng.choice([8, 9, 10]),   # 合法枚举只有这三个
            "use_type": 0,
            "succession_num": 0,
        })

        tc.append(base)
        obj["data"]["trained_chara"] = tc

        size = _save_template(con, obj)
        con.commit()

        return {
            "ok": True,
            "same_card": bool(same),
            "trained_chara_id": base["trained_chara_id"],
            "card_id": card_id,
            "attrs": {k: base[k] for k in ("speed", "stamina", "power", "guts", "wiz")},
            "rank_score": score,
            "template_size": size,
            "total": len(tc),
        }
    finally:
        con.close()


if __name__ == "__main__":
    import sys
    DB = r"C:/Users/Schwarz/uma_replay/offline.db"
    con = sqlite3.connect(DB)
    cards = list_valid_cards(con)
    con.close()
    print(f"合法 card_id 共 {len(cards)} 个: {cards[:10]}…")

    r = add_trained_chara(DB, seed=12345)
    print(f"\n新增: trained_chara_id={r['trained_chara_id']} card_id={r['card_id']}")
    print(f"  五维: {r['attrs']}")
    print(f"  评分: {r['rank_score']}")
    print(f"  模板: {r['template_size']} B, 总计 {r['total']} 条")
