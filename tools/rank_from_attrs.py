"""按 race_entry 的马属性算出名次，写进 force_rank.txt 供插件读取。

比赛名次由客户端用自己的模拟算出（不是剧本里的 finishTime），
但模拟输入是马属性。这里用同一套物理模型预估名次，
再让插件的 GetResult hook 把结果钉死，保证和服务器一致。

用法（服务器在 race_entry 被请求时调用）：
    from rank_from_attrs import compute_and_write
    compute_and_write(con, distance=3200)
"""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path

FORCE_FILE = Path(r"C:/Users/Schwarz/uma_replay/force_rank.txt")

# 与 gen_race_distance.py 一致的模型
V_BASE = 17.6
V_DIST_DECAY = 0.00035
V_SPEED_K = 0.18
SPURT_START = 0.72
SPURT_MULT = 1.16
START_ACCEL_FRAMES = 8



MASTER = Path(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/"
              r"UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb")

# ultimate_race_id → 赛道距离（从 master 查，缓存）
_DIST_CACHE: dict[int, float] = {}


def distance_of(ultimate_race_id: int | None) -> float:
    """按 ultimate_race_id 查赛道距离（米）。查不到返回 1600。"""
    if not ultimate_race_id:
        return 1600.0
    if ultimate_race_id in _DIST_CACHE:
        return _DIST_CACHE[ultimate_race_id]
    dist = 1600.0
    try:
        mc = sqlite3.connect(f"file:{MASTER}?mode=ro", uri=True)
        row = mc.execute(
            """SELECT rcs.distance FROM ultimate_race_contents urc
               JOIN race_instance ri ON ri.id = urc.race_instance_id
               JOIN race r ON r.id = ri.race_id
               JOIN race_course_set rcs ON rcs.id = r.course_set
               WHERE urc.id = ?""",
            (ultimate_race_id,)).fetchone()
        mc.close()
        if row and row[0]:
            dist = float(row[0])
    except Exception:
        pass
    _DIST_CACHE[ultimate_race_id] = dist
    return dist


def base_speed(distance: float) -> float:
    return V_BASE - (distance - 1600) * V_DIST_DECAY


def effective_time(speed: int, stamina: int, distance: float,
                   style: int = 2, motivation: int = 4) -> float:
    """估算完赛时间（秒）。越小越快。"""
    v = base_speed(distance)
    v *= (max(speed, 100) / 1000.0) ** V_SPEED_K
    v *= {1: 0.96, 2: 0.98, 3: 1.0, 4: 1.02, 5: 1.04}.get(motivation, 1.0)
    early, late = {1: (1.03, 0.97), 2: (1.00, 1.00),
                   3: (0.97, 1.05), 4: (0.94, 1.09)}.get(style, (1.0, 1.0))
    avg_m = (early + late) / 2
    # 冲刺收益
    spurt_bonus = 1 + (SPURT_MULT - 1) * (1 - SPURT_START) * 0.5
    # 起跑损失
    accel_loss = 1 - 0.0325 * START_ACCEL_FRAMES / 100
    # 耐力不足惩罚
    hp_need = distance / (v * avg_m)
    hp_have = (distance + 0.8 * 0.889 * max(stamina, 1)) / (v * avg_m)
    penalty = 1.0
    if hp_have < hp_need * 0.95:
        penalty = 1.0 + (hp_need * 0.95 - hp_have) / hp_need * 0.15
    return distance / (v * avg_m * spurt_bonus * accel_loss) * penalty


def compute_ranks(horses: list[dict], distance: float) -> list[tuple[int, float, int]]:
    """返回 [(原始索引, 估算时间, 名次1based)]。"""
    times = []
    for i, h in enumerate(horses):
        t = effective_time(
            h.get("speed") or 1000,
            h.get("stamina") or 1000,
            distance,
            h.get("running_style") or 2,
            h.get("motivation") or 4,
        )
        times.append((i, t))
    ranked = sorted(times, key=lambda x: x[1])
    out = []
    for rank, (i, t) in enumerate(ranked, 1):
        out.append((i, t, rank))
    return out


def compute_and_write(con: sqlite3.Connection, distance: float = 3200) -> str:
    """读 race_entry，算名次，写 force_rank.txt。返回描述。"""
    import msgpack

    r = con.execute("SELECT data FROM response_cache WHERE path='ultimate_race/race_entry'").fetchone()
    if not r:
        return "库里没有 race_entry"

    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    horses = (obj.get("data") or {}).get("race_horse_data_array") or []
    if not horses:
        return "race_entry 没有马数组"

    ranks = compute_ranks(horses, distance)
    order = [i for i, t, rk in sorted(ranks, key=lambda x: x[2])]

    # 玩家 = 马 0
    player_rank = next(rk for i, t, rk in ranks if i == 0)
    player_pos = horses[0].get("frame_order")
    player_idx = (player_pos - 1) if isinstance(player_pos, int) and player_pos > 0 else 0

    # 写完整名次表："idx:rank,idx:rank,..."（rank 1-based）
    # 注意：ranks 里的 i 是数组位置，force_rank 的 idx 要的是剧本位置（frame_order-1）
    def script_pos(arr_idx: int) -> int | None:
        fo = horses[arr_idx].get("frame_order")
        if isinstance(fo, int) and fo > 0:
            return fo - 1
        return None

    pairs_list = []
    for i, t, rk in sorted(ranks, key=lambda x: x[2]):
        sp = script_pos(i)
        if sp is not None:
            pairs_list.append(f"{sp}:{rk}")
    pairs = ",".join(pairs_list)
    FORCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    FORCE_FILE.write_text(pairs, encoding="utf-8")

    detail = " / ".join(f"idx{i}={t:.1f}s(第{rk})" for i, t, rk in ranks[:5])
    return (f"{len(horses)} 马，玩家 idx{player_idx} → 预估第 {player_rank} 名；"
            f"front5: {detail}")


if __name__ == "__main__":
    BASE = Path(r"C:/Users/Schwarz/uma_replay")
    con = sqlite3.connect(f"file:{BASE/'offline.db'}?mode=ro", uri=True)
    print(compute_and_write(con, 3200))
    con.close()
    print(f"\nforce_rank.txt = {FORCE_FILE.read_text().strip()}")
