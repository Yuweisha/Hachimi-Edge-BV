"""赛马娘 Rank 段位映射（基于 master.mdb 的 single_mode_rank 表）。

分段规则：
  id  1-9   → G / F / E / D / C / B / A / S / SS          （9 个，无数字）
  id 10-17  → UG / UF / UE / UD / UC / UB / UA / US       （8 个基名，无数字）
  id 18-89  → UG1..UG9, UF1..UF9, ... UA9, US1..US9       （8×9 = 72）
  id 90-113 → LG1 .. LG24                                  （24 个）
  id 114    → LF                                           （终极）
"""
from __future__ import annotations

import sqlite3

MASTER_MDB = (r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/"
              r"UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb")

# 前 9 段（无数字）
TIER_BASIC = ["G", "F", "E", "D", "C", "B", "A", "S", "SS"]
# U 系列基名（按 id 10→17 顺序）
TIER_U = ["UG", "UF", "UE", "UD", "UC", "UB", "UA", "US"]

ID_U_FIRST = 10     # UG
ID_U_NUM_FIRST = 18 # UG1
ID_LG_FIRST = 90    # LG1
ID_LF = 114         # LF
ID_MAX = 298        # 表内最大 id（之后统一视为 LF）


def rank_label(rank_id: int) -> str:
    """把 rank 字段换成段位名（UG5 / UE2 / UD9 这种）。

    规律（8 个数据点验证）：rank 每 +1 = 升一小段。
      rank 19 = UG, 20~28 = UG1~UG9, 29 = UF, ...
      rank 39 = UE（实测 29008 分）
      rank 45 = UE6（实测 32444 分）
      rank 58 = UD9（实测 40521 分）
      rank 68 = UC9（实测 47301 分）
      rank 78 = UB9（实测 54449 分）
    """
    if rank_id <= 0:
        return "-"

    TIER = ["UG", "UF", "UE", "UD", "UC", "UB", "UA", "US"]

    if rank_id >= 19:
        offset = rank_id - 19
        big = offset // 10
        sub = offset % 10

        if big < len(TIER):
            name = TIER[big]
            return name if sub == 0 else f"{name}{sub}"

        # 超出 US9 → LG（rank 99 = LG1）
        lg = rank_id - 99 + 1
        return f"LG{lg}" if 1 <= lg <= 24 else "LF"

    # rank 1~18：基础段位，客户端带 + 变体（低段无样本，按递增给出）
    basic = ["G", "F", "F+", "E", "E+", "D", "D+", "C", "C+",
             "B", "B+", "A", "A+", "S", "S+", "SS", "SS+"]
    if 1 <= rank_id <= len(basic):
        return basic[rank_id - 1]
    return f"R{rank_id}"


def load_rank_table(mdb: str = MASTER_MDB) -> list[tuple[int, int, int]]:
    """读 (id, min_value, max_value) 列表。"""
    con = sqlite3.connect(f"file:{mdb}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT id, min_value, max_value FROM single_mode_rank ORDER BY id"
        ).fetchall()
    finally:
        con.close()


def rank_from_score(score: int, table: list[tuple[int, int, int]] | None = None) -> int:
    """按评分反查 rank id。"""
    if table is None:
        try:
            table = load_rank_table()
        except Exception:
            return 0
    for rid, lo, hi in table:
        if lo <= score <= hi:
            return rid
    return table[-1][0] if table else 0


def label_from_score(score: int, table: list[tuple[int, int, int]] | None = None) -> str:
    return rank_label(rank_from_score(score, table))


if __name__ == "__main__":
    table = load_rank_table()
    print(f"rank 表 {len(table)} 条\n")

    # 关键节点
    for rid in (1, 9, 10, 17, 18, 26, 27, 89, 90, 113, 114, 200, 298):
        lo = hi = 0
        for r, a, b in table:
            if r == rid:
                lo, hi = a, b
                break
        print(f"  id={rid:4}  {rank_label(rid):8}  {lo:>7} ~ {hi:>7}")

    print("\n=== 分段统计 ===")
    from collections import Counter
    c = Counter(rank_label(r) for r, _, _ in table)
    print(f"  唯一段位: {len(c)}")
    # 检查连续性
    for prefix in TIER_U:
        nums = sorted(int(k[len(prefix):]) for k in c if k.startswith(prefix) and k != prefix and k[len(prefix):].isdigit())
        print(f"  {prefix}: {len(nums)} 段, {nums[:3]}…{nums[-3:] if nums else ''}")
    lg = sorted(int(k[2:]) for k in c if k.startswith("LG") and k[2:].isdigit())
    print(f"  LG: {len(lg)} 段, {lg[0]}~{lg[-1]}")
    print(f"  LF: {c.get('LF', 0)} 条")
