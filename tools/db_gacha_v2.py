"""抽卡的数据库层 v2：全量卡池 + 权重表 + 抽卡逻辑 + 结果落库。

为什么不用 gacha_id：
  实测 30476/30477 今天上午已过期，30478 在 master 里根本不存在（新池 master 未更新）。
  依赖 gacha_id 会抽不出卡。改为按 card_type 从**全量真实卡池**抽。

表结构：
  card_pool    (card_type, card_id, rarity)  全量卡池（角色卡 + 支援卡）
  gacha_pool   (gacha_id, card_id, card_type, rarity)  按池的索引（可选，优先用）
  gacha_weight (rarity, weight)              稀有度权重

卡池来源：
  card_type=1 角色卡  ← master.card_rarity_data (card_id, rarity)
  card_type=2 支援卡  ← master.support_card_data (id, rarity)

用法：
  python db_gacha_v2.py --import
  python db_gacha_v2.py --stats
  python db_gacha_v2.py --draw 1 10
  python db_gacha_v2.py --draw 2 10
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

DEFAULT_WEIGHTS = {3: 0.03, 2: 0.18, 1: 0.79}

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS card_pool (
  card_type INTEGER NOT NULL,
  card_id   INTEGER NOT NULL,
  rarity    INTEGER NOT NULL,
  PRIMARY KEY (card_type, card_id)
);
CREATE INDEX IF NOT EXISTS idx_cardpool ON card_pool(card_type, rarity);

CREATE TABLE IF NOT EXISTS gacha_pool (
  gacha_id  INTEGER NOT NULL,
  card_id   INTEGER NOT NULL,
  card_type INTEGER NOT NULL,
  rarity    INTEGER NOT NULL,
  PRIMARY KEY (gacha_id, card_id, card_type)
);

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

    # 角色卡的抽卡稀有度是 card_data.default_rarity
    # （card_rarity_data.rarity 是觉醒/突破等级 1-5，不是抽卡稀有度）
    mcur.execute("SELECT id, default_rarity FROM card_data")
    chara_cards = [(1, int(cid), int(rar)) for cid, rar in mcur.fetchall()
                   if int(rar) in (1, 2, 3)]

    mcur.execute("SELECT id, rarity FROM support_card_data")
    support_cards = [(2, int(cid), int(rar)) for cid, rar in mcur.fetchall()
                     if int(rar) in (1, 2, 3)]

    mcur.execute("SELECT gacha_id, card_id, card_type, rarity FROM gacha_available")
    gacha_rows = mcur.fetchall()
    mc.close()

    with conn() as con:
        con.execute("DELETE FROM card_pool")
        con.executemany(
            "INSERT OR REPLACE INTO card_pool(card_type, card_id, rarity) VALUES (?,?,?)",
            chara_cards + support_cards)
        con.execute("DELETE FROM gacha_pool")
        con.executemany(
            "INSERT OR REPLACE INTO gacha_pool(gacha_id, card_id, card_type, rarity) "
            "VALUES (?,?,?,?)", gacha_rows)
        con.commit()

        for ct, name in ((1, "角色卡"), (2, "支援卡")):
            rows = con.execute(
                "SELECT rarity, COUNT(*) FROM card_pool WHERE card_type=? GROUP BY rarity "
                "ORDER BY rarity", (ct,)).fetchall()
            print(f"  {name}: {sum(r[1] for r in rows)} 张  {dict(rows)}")
        n_pool = con.execute("SELECT COUNT(DISTINCT gacha_id) FROM gacha_pool").fetchone()[0]
        print(f"  gacha_pool 索引: {len(gacha_rows):,} 行 / {n_pool} 个池")


def weights() -> dict[int, float]:
    ensure_schema()
    with conn() as con:
        rows = con.execute("SELECT rarity, weight FROM gacha_weight").fetchall()
    return {int(r): float(w) for r, w in rows}


def _pick(pool: dict[int, list[int]], w: dict[int, float],
          rng: random.SystemRandom) -> tuple[int, int] | None:
    rs = [r for r in pool if r in w and pool[r]]
    if not rs:
        return None
    ws = [w[r] for r in rs]
    r = rng.choices(rs, weights=ws, k=1)[0]
    return rng.choice(pool[r]), r


def _pool_rows(gacha_id: int, card_type: int) -> list[tuple]:
    """从 gacha_pool 取该池的卡，返回 (card_id, rarity, odds, is_pickup)。"""
    with conn() as con:
        return con.execute(
            "SELECT card_id, rarity, odds, is_pickup FROM gacha_pool "
            "WHERE gacha_id=? AND card_type=? AND odds > 0",
            (gacha_id, card_type)).fetchall()


def _guarantee(gacha_id: int) -> tuple[int, int]:
    """读保底配置：返回 (rarity, num)。读不到返回 (0, 0)。"""
    try:
        mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
        r = mc.execute(
            "SELECT draw_guarantee_rarity, draw_guarantee_num FROM gacha_data WHERE id=?",
            (gacha_id,)).fetchone()
        mc.close()
        if r and r[0] and r[1]:
            return int(r[0]), int(r[1])
    except Exception:
        pass
    return 0, 0


def draw(card_type: int = 1, n: int = 10, gacha_id: int | None = None) -> list[tuple[int, int, int]]:
    """抽卡。返回 [(card_id, card_type, rarity)]。

    优先用真实卡池（gacha_available.odds 加权，UP 卡的 odds 已含加成），
    并按 gacha_data 的 draw_guarantee_rarity/num 做十连保底。
    """
    ensure_schema()
    rng = random.SystemRandom()

    # ---- 1) 真实池：按 odds 加权 ----
    if gacha_id:
        rows = _pool_rows(gacha_id, card_type)
        if rows:
            ids = [r[0] for r in rows]
            rars = [r[1] for r in rows]
            odds = [max(1, r[2]) for r in rows]

            picked = rng.choices(range(len(rows)), weights=odds, k=n)
            cards = [(ids[i], card_type, rars[i]) for i in picked]

            # ---- 2) 十连保底 ----
            if n >= 10:
                gr_rar, gr_num = _guarantee(gacha_id)
                if gr_rar > 0 and gr_num > 0:
                    have = sum(1 for _c, _t, r in cards if r >= gr_rar)
                    if have < gr_num:
                        # 从该稀有度及以上的卡里按 odds 补
                        elig = [(i, r) for i, r in zip(ids, rars) if r >= gr_rar]
                        if elig:
                            e_ids = [e[0] for e in elig]
                            e_rars = [e[1] for e in elig]
                            e_odds = [max(1, rows[ids.index(ei)][2]) for ei in e_ids]
                            need = gr_num - have
                            for _ in range(need):
                                j = rng.choices(range(len(e_ids)), weights=e_odds, k=1)[0]
                                cards[-1] = (e_ids[j], card_type, e_rars[j])
            return cards

    # ---- 3) 回退：全量卡池 + 稀有度权重 ----
    w = weights()
    with conn() as con:
        rows = con.execute(
            "SELECT card_id, rarity FROM card_pool WHERE card_type=?",
            (card_type,)).fetchall()
    pool: dict[int, list[int]] = {}
    for cid, rar in rows:
        pool.setdefault(int(rar), []).append(int(cid))
    if not pool:
        return []

    out: list[tuple[int, int, int]] = []
    for _ in range(n):
        got = _pick(pool, w, rng)
        if got:
            cid, rar = got
            out.append((cid, card_type, rar))

    # ---- 4) 十连保底（回退分支同样适用）----
    # 池子查不到时也要保底，否则全 1★ 会被玩家当成 bug
    if n >= 10 and out:
        gr_rar, gr_num = (0, 0)
        if gacha_id:
            gr_rar, gr_num = _guarantee(gacha_id)
        if gr_rar <= 0 or gr_num <= 0:
            # master 查不到就用默认：十连保底 2★ ×1
            gr_rar, gr_num = 2, 1
        have = sum(1 for _c, _t, r in out if r >= gr_rar)
        if have < gr_num:
            elig = [r for r in pool if r >= gr_rar]
            if elig:
                e_ids: list[int] = []
                e_rars: list[int] = []
                for r in elig:
                    for cid in pool[r]:
                        e_ids.append(cid)
                        e_rars.append(r)
                if e_ids:
                    need = gr_num - have
                    for _ in range(need):
                        j = rng.randrange(len(e_ids))
                        out[-1] = (e_ids[j], card_type, e_rars[j])
    return out


def gacha_cost(gacha_id: int | None, draw_num: int) -> int:
    """查抽卡成本（宝石）。查不到按 150/抽。"""
    unit = 150
    if gacha_id:
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            r = mc.execute("SELECT cost_single FROM gacha_data WHERE id=?",
                           (gacha_id,)).fetchone()
            mc.close()
            if r and r[0] and int(r[0]) > 0:
                unit = int(r[0])
        except Exception:
            pass
    return unit * draw_num


def charge_gacha(gacha_id: int | None, draw_num: int) -> dict:
    """扣宝石：优先 fcoin（免费），不足扣 coin（付费）。"""
    cost = gacha_cost(gacha_id, draw_num)
    ensure_schema()
    with conn() as con:
        def get(k, d=0):
            r = con.execute("SELECT value FROM user_state WHERE key=?", (k,)).fetchone()
            return int(r[0]) if r else d

        fcoin = get("fcoin")
        coin = get("coin")
        if fcoin + coin < cost:
            return {"cost": cost, "fcoin": fcoin, "coin": coin, "ok": False}

        use_f = min(fcoin, cost)
        fcoin -= use_f
        coin -= (cost - use_f)
        con.execute("INSERT OR REPLACE INTO user_state(key,value) VALUES ('fcoin',?)", (str(fcoin),))
        con.execute("INSERT OR REPLACE INTO user_state(key,value) VALUES ('coin',?)", (str(coin),))
        con.commit()
    return {"cost": cost, "fcoin": fcoin, "coin": coin, "ok": True}


def commit_draw(gacha_id: int, cards: list[tuple[int, int, int]]) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn() as con:
        for cid, ct, rar in cards:
            con.execute(
                "INSERT INTO gacha_log(gacha_id, card_type, card_id, new_flag, drawn_at) "
                "VALUES (?,?,?,0,?)", (gacha_id, ct, cid, ts))
            con.execute(
                "INSERT OR IGNORE INTO owned_card(card_id, rarity, talent_level, "
                "create_time, skill_data) VALUES (?,?,1,?,X'90')", (cid, rar, ts))
        con.commit()


def stats() -> None:
    ensure_schema()
    with conn() as con:
        print("=== card_pool ===")
        for ct, name in ((1, "角色卡"), (2, "支援卡")):
            rows = con.execute(
                "SELECT rarity, COUNT(*) FROM card_pool WHERE card_type=? GROUP BY rarity "
                "ORDER BY rarity", (ct,)).fetchall()
            print(f"  {name}: {sum(r[1] for r in rows)} 张  {dict(rows)}")
        n = con.execute("SELECT COUNT(*) FROM gacha_pool").fetchone()[0]
        print(f"\ngacha_pool: {n:,} 行")
        print("\n=== 权重 ===")
        for r, wt in con.execute("SELECT rarity, weight FROM gacha_weight ORDER BY rarity DESC"):
            print(f"  {r}★ = {wt*100:.1f}%")
        print(f"\ngacha_log: {con.execute('SELECT COUNT(*) FROM gacha_log').fetchone()[0]} 条")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="do_import", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--draw", nargs=2, metavar=("CARD_TYPE", "N"))
    ap.add_argument("--gacha-id", type=int, default=None)
    a = ap.parse_args()

    if a.do_import:
        print("=== 导入卡池 ===")
        import_pools()
    if a.stats or not any([a.do_import, a.draw]):
        stats()
    if a.draw:
        ct, n = int(a.draw[0]), int(a.draw[1])
        cards = draw(ct, n, a.gacha_id)
        from collections import Counter
        print(f"\n抽 {n} 次 (card_type={ct}):")
        for cid, _ct, rar in cards:
            print(f"  card_id={cid} {rar}★")
        cnt = Counter(r for _, _, r in cards)
        print(f"\n统计: {dict(sorted(cnt.items(), reverse=True))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
