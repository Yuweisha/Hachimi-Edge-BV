"""抽卡的数据库层：卡池权重表 + 抽卡逻辑 + 结果落库。

卡池来源：master.mdb 的 gacha_available（gacha_id, card_id, card_type, rarity）
权重来源：gacha_weight 表（可调，默认 3★/2★/1★ = 3%/18%/79%）

表结构：
  gacha_pool    (gacha_id, card_id, card_type, rarity)  卡池内容
  gacha_weight  (rarity, weight)                        稀有度权重
  gacha_log     抽卡历史（db_init 已建）

用法：
  python db_gacha.py --import          # 从 master 导入所有卡池
  python db_gacha.py --stats           # 查看卡池统计
  python db_gacha.py --draw 30478 10   # 试抽一次
"""
from __future__ import annotations

import argparse
import random
import sqlite3
import time
from pathlib import Path

BASE = Path(r"C:/Users/Schwarz/uma_replay")
DB_PATH = BASE / "offline.db"
MDB = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb"

# 默认权重：3★ 3%、2★ 18%、1★ 79%
DEFAULT_WEIGHTS = {3: 0.03, 2: 0.18, 1: 0.79}

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS gacha_pool (
  gacha_id  INTEGER NOT NULL,
  card_id   INTEGER NOT NULL,
  card_type INTEGER NOT NULL,
  rarity    INTEGER NOT NULL,
  PRIMARY KEY (gacha_id, card_id, card_type)
);
CREATE INDEX IF NOT EXISTS idx_pool_gacha ON gacha_pool(gacha_id);

CREATE TABLE IF NOT EXISTS gacha_weight (
  rarity INTEGER PRIMARY KEY,
  weight REAL NOT NULL
);
"""


def conn() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH), timeout=10)


def ensure_schema() -> None:
    with conn() as con:
        con.executescript(SCHEMA)
        for r, w in DEFAULT_WEIGHTS.items():
            con.execute("INSERT OR IGNORE INTO gacha_weight(rarity, weight) VALUES (?,?)", (r, w))
        con.commit()


def import_pools() -> None:
    ensure_schema()
    mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
    mcur = mc.cursor()
    mcur.execute("SELECT gacha_id, card_id, card_type, rarity FROM gacha_available")
    rows = mcur.fetchall()
    mc.close()

    with conn() as con:
        con.execute("DELETE FROM gacha_pool")
        con.executemany(
            "INSERT OR REPLACE INTO gacha_pool(gacha_id, card_id, card_type, rarity) "
            "VALUES (?,?,?,?)", rows)
        con.commit()
        n = con.execute("SELECT COUNT(*) FROM gacha_pool").fetchone()[0]
        pools = con.execute("SELECT COUNT(DISTINCT gacha_id) FROM gacha_pool").fetchone()[0]
    print(f"导入卡池: {n:,} 行，{pools} 个池")


def weights() -> dict[int, float]:
    ensure_schema()
    with conn() as con:
        rows = con.execute("SELECT rarity, weight FROM gacha_weight").fetchall()
    return {int(r): float(w) for r, w in rows}


def draw(gacha_id: int, n: int = 10) -> list[tuple[int, int, int]]:
    """抽卡。返回 [(card_id, card_type, rarity)]。

    策略：
      - 按 card_type 分组（1=角色池优先，2=支援池）
      - 用 gacha_weight 决定稀有度
      - 同稀有度内均匀随机
    """
    ensure_schema()
    with conn() as con:
        rows = con.execute(
            "SELECT card_id, card_type, rarity FROM gacha_pool WHERE gacha_id=?",
            (gacha_id,)).fetchall()
    if not rows:
        return []

    by_type: dict[int, dict[int, list[int]]] = {}
    for cid, ct, rar in rows:
        by_type.setdefault(ct, {}).setdefault(rar, []).append(cid)

    w = weights()
    out: list[tuple[int, int, int]] = []
    rng = random.SystemRandom()

    for _ in range(n):
        ct = 1 if 1 in by_type else next(iter(by_type))
        rp = by_type[ct]
        rs = [r for r in rp if r in w and rp[r]]
        if not rs:
            continue
        ws = [w[r] for r in rs]
        r = rng.choices(rs, weights=ws, k=1)[0]
        cid = rng.choice(rp[r])
        out.append((cid, ct, r))
    return out


def commit_draw(gacha_id: int, cards: list[tuple[int, int, int]]) -> None:
    """把抽卡结果落库：写日志 + 补 owned_card。"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn() as con:
        for cid, ct, rar in cards:
            con.execute(
                "INSERT INTO gacha_log(gacha_id, card_type, card_id, new_flag, drawn_at) "
                "VALUES (?,?,?,0,?)", (gacha_id, ct, cid, ts))
            if ct == 1:
                # 角色卡：card_id 100101 -> chara_id 1001
                con.execute(
                    "INSERT OR IGNORE INTO owned_card(card_id, rarity, talent_level, "
                    "create_time, skill_data) VALUES (?,?,1,?,X'80')",
                    (cid, rar, ts))
            elif ct == 2:
                con.execute(
                    "INSERT OR IGNORE INTO owned_card(card_id, rarity, talent_level, "
                    "create_time, skill_data) VALUES (?,?,1,?,X'80')",
                    (cid, rar, ts))
        con.commit()


def stats() -> None:
    ensure_schema()
    with conn() as con:
        n = con.execute("SELECT COUNT(*) FROM gacha_pool").fetchone()[0]
        print(f"卡池总行数: {n:,}")
        rows = con.execute(
            "SELECT gacha_id, COUNT(*) c FROM gacha_pool GROUP BY gacha_id "
            "ORDER BY c DESC LIMIT 10").fetchall()
        print("\n最大的 10 个池:")
        for gid, c in rows:
            print(f"  gacha_id={gid}: {c} 张")
        print("\n权重:")
        for r, w in con.execute("SELECT rarity, weight FROM gacha_weight ORDER BY rarity DESC"):
            print(f"  {r}★ = {w*100:.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="do_import", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--draw", nargs=2, metavar=("GACHA_ID", "N"))
    a = ap.parse_args()

    if a.do_import:
        import_pools()
    if a.stats or not any([a.do_import, a.draw]):
        stats()
    if a.draw:
        gid, n = int(a.draw[0]), int(a.draw[1])
        cards = draw(gid, n)
        print(f"\n抽 {n} 次 (gacha_id={gid}):")
        from collections import Counter
        cnt = Counter(r for _, _, r in cards)
        for cid, ct, rar in cards:
            print(f"  card_id={cid} type={ct} {rar}★")
        print(f"\n统计: {dict(sorted(cnt.items(), reverse=True))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
