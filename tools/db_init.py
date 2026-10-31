"""离线服务器数据库层 —— 用户状态 + 派生数据。

设计原则：
  1. 只存"玩家状态"，不存 master 数据（master.mdb 里已有）
  2. 所有 ID 必须真实（来自 master.mdb），绝不伪造
  3. 可推导的接口从这里生成，不可推导的回落 replay.bin

表结构：
  user_state        键值对（coin/fcoin/各种计数）
  owned_chara       拥有的角色（chara_id + 亲爱度等）
  owned_card        拥有的卡
  owned_cloth       拥有的服装
  unlocked_event    已解锁的育成事件
  story_state       主线/角色剧情进度
  gacha_log         抽卡记录
  meta              版本戳

用法：
  python db_init.py                  # 建库并初始化（幂等）
  python db_init.py --reset          # 清空重建
  python db_init.py --from-replay    # 从当前 replay.bin 的 load/index 导入状态
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import struct
import time
from pathlib import Path

import msgpack

BASE = Path(r"C:/Users/Schwarz/uma_replay")
DB_PATH = BASE / "offline.db"
REPLAY = BASE / "replay.bin"
DECL = BASE / "path_declared.json"
MDB = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS user_state (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS owned_chara (
  chara_id       INTEGER PRIMARY KEY,
  training_num   INTEGER NOT NULL DEFAULT 0,
  love_point     INTEGER NOT NULL DEFAULT 0,
  fan            INTEGER NOT NULL DEFAULT 0,
  max_grade      INTEGER NOT NULL DEFAULT 1,
  dress_id       INTEGER NOT NULL DEFAULT 0,
  mini_dress_id  INTEGER NOT NULL DEFAULT 2,
  dress_color_id INTEGER NOT NULL DEFAULT 0,
  mini_dress_color_id INTEGER NOT NULL DEFAULT 0,
  create_time    TEXT NOT NULL,
  love_point_pool INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS owned_card (
  card_id      INTEGER PRIMARY KEY,
  rarity       INTEGER NOT NULL DEFAULT 1,
  talent_level INTEGER NOT NULL DEFAULT 1,
  create_time  TEXT NOT NULL,
  skill_data   BLOB
);

CREATE TABLE IF NOT EXISTS owned_cloth (
  cloth_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS unlocked_event (
  story_id    INTEGER PRIMARY KEY,
  chara_id    INTEGER NOT NULL,
  unlocked_at TEXT NOT NULL,
  new_flag    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ev_chara ON unlocked_event(chara_id);

CREATE TABLE IF NOT EXISTS story_state (
  episode_id  INTEGER PRIMARY KEY,
  state       INTEGER NOT NULL DEFAULT 1,
  updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gacha_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  gacha_id    INTEGER NOT NULL,
  card_type   INTEGER NOT NULL,
  card_id     INTEGER NOT NULL,
  new_flag    INTEGER NOT NULL DEFAULT 0,
  drawn_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

DEFAULT_STATE = {
    "coin": "100000000",
    "fcoin": "100000000",
    "gold_item": "100000000",     # item_id 59
    "key_item": "9999",           # item_id 190
    "viewer_id": "601653962",
    "schema_version": "1",
}


def master_conn():
    return sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)


def read_replay_loadindex():
    """从 replay.bin 读出当前 load/index（用于迁移初始状态）"""
    try:
        decl = json.loads(DECL.read_text(encoding="utf-8"))
        want = decl.get("load/index")
        b = REPLAY.read_bytes()
        n = struct.unpack_from("<I", b, 4)[0]
        off = 8
        for _ in range(n):
            _a, d, dl = struct.unpack_from("<III", b, off)
            off += 12
            if d == want:
                v = msgpack.unpackb(b[off:off + dl], raw=False,
                                    strict_map_key=False, unicode_errors="replace")
                return v.get("data", {})
            off += dl
    except Exception as e:
        print("读取 replay load/index 失败:", e)
    return None


def init_state(con: sqlite3.Connection, from_replay: bool) -> None:
    cur = con.cursor()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    # ---- 基础状态 ----
    for k, v in DEFAULT_STATE.items():
        cur.execute("INSERT OR REPLACE INTO user_state(key, value) VALUES (?, ?)", (k, v))

    mc = master_conn()
    mcur = mc.cursor()

    # master 权威数据
    mcur.execute("SELECT id FROM chara_data WHERE start_date <= date('now')")
    all_chara = {r[0] for r in mcur.fetchall()}
    mcur.execute("SELECT id, chara_id FROM dress_data")
    dress_rows = mcur.fetchall()
    dress_by_chara: dict[int, list[int]] = {}
    for did, cid in dress_rows:
        dress_by_chara.setdefault(cid, []).append(did)
    all_dress = {r[0] for r in dress_rows}
    mcur.execute("SELECT id FROM card_data")
    all_card = {r[0] for r in mcur.fetchall()}
    mcur.execute("SELECT story_id, card_chara_id FROM single_mode_story_data WHERE gallery_flag=1")
    gal_rows = mcur.fetchall()
    mcur.execute("SELECT id FROM chara_story_data")
    cs_ids = [r[0] for r in mcur.fetchall()]
    mc.close()

    gid_to_chara = {sid: cid for sid, cid in gal_rows}

    if from_replay:
        li = read_replay_loadindex()
        if not li:
            print("无法从 replay 读取 load/index，改用全量初始化")
            from_replay = False

    if from_replay and li:
        # ---- 从 replay 导入 ----
        n_chara = n_card = n_cloth = n_ev = 0
        for c in li.get("chara_list") or []:
            if not isinstance(c, dict):
                continue
            cid = c.get("chara_id")
            if cid not in all_chara:
                continue
            cur.execute("""INSERT OR REPLACE INTO owned_chara
                (chara_id, training_num, love_point, fan, max_grade, dress_id,
                 mini_dress_id, dress_color_id, mini_dress_color_id, create_time, love_point_pool)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (cid, c.get("training_num", 0), c.get("love_point", 0), c.get("fan", 0),
                 c.get("max_grade", 1), c.get("dress_id", 0),
                 c.get("mini_dress_id", 2), c.get("dress_color_id", 0),
                 c.get("mini_dress_color_id", 0),
                 c.get("create_time", now_str), c.get("love_point_pool", 0)))
            n_chara += 1

        for c in li.get("card_list") or []:
            if not isinstance(c, dict):
                continue
            cid = c.get("card_id")
            if cid not in all_card:
                continue
            sk = c.get("skill_data_array") or []
            cur.execute("""INSERT OR REPLACE INTO owned_card
                (card_id, rarity, talent_level, create_time, skill_data)
                VALUES (?,?,?,?,?)""",
                (cid, c.get("rarity", 1), c.get("talent_level", 1),
                 c.get("create_time", now_str),
                 msgpack.packb(sk, use_bin_type=True)))
            n_card += 1

        for c in li.get("cloth_list") or []:
            if not isinstance(c, dict):
                continue
            cid = c.get("cloth_id")
            if cid not in all_dress:
                continue
            cur.execute("INSERT OR IGNORE INTO owned_cloth(cloth_id) VALUES (?)", (cid,))
            n_cloth += 1

        for e in li.get("event_data_array") or []:
            if not isinstance(e, dict):
                continue
            sid = e.get("data_id")
            if sid not in gid_to_chara:
                continue
            cur.execute("""INSERT OR IGNORE INTO unlocked_event
                (story_id, chara_id, unlocked_at, new_flag) VALUES (?,?,?,?)""",
                (sid, gid_to_chara[sid], e.get("create_time", now_str),
                 e.get("new_flag", 0)))
            n_ev += 1

        for cs in li.get("character_story_data_list") or []:
            if not isinstance(cs, dict):
                continue
            eid = cs.get("episode_id")
            if eid:
                cur.execute("""INSERT OR IGNORE INTO story_state
                    (episode_id, state, updated_at) VALUES (?,?,?)""",
                    (eid, cs.get("state", 1), now_str))

        print(f"从 replay 导入: chara={n_chara} card={n_card} cloth={n_cloth} event={n_ev}")

    else:
        # ---- 全量初始化（所有实装角色/卡/服装/事件）----
        for cid in sorted(all_chara):
            dress = sorted(dress_by_chara.get(cid, []))
            cur.execute("""INSERT OR REPLACE INTO owned_chara
                (chara_id, training_num, love_point, fan, max_grade, dress_id,
                 mini_dress_id, dress_color_id, mini_dress_color_id, create_time, love_point_pool)
                VALUES (?,0,0,0,1,?,2,0,0,?,0)""",
                (cid, dress[0] if dress else 1, now_str))
        for cid in sorted(all_card):
            cur.execute("""INSERT OR REPLACE INTO owned_card
                (card_id, rarity, talent_level, create_time, skill_data) VALUES (?,1,1,?,?)""",
                (cid, now_str, msgpack.packb([], use_bin_type=True)))
        for did in sorted(all_dress):
            cur.execute("INSERT OR IGNORE INTO owned_cloth(cloth_id) VALUES (?)", (did,))
        for sid, cid in gal_rows:
            cur.execute("""INSERT OR IGNORE INTO unlocked_event
                (story_id, chara_id, unlocked_at, new_flag) VALUES (?,?,?,0)""",
                (sid, cid, now_str))
        for eid in cs_ids:
            cur.execute("""INSERT OR IGNORE INTO story_state
                (episode_id, state, updated_at) VALUES (?,1,?)""", (eid, now_str))
        print(f"全量初始化: chara={len(all_chara)} card={len(all_card)} "
              f"cloth={len(all_dress)} event={len(gal_rows)} story={len(cs_ids)}")

    cur.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('init_at', ?)", (now_str,))
    con.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--from-replay", action="store_true", default=True)
    ap.add_argument("--full", action="store_true", help="全量初始化而不是从 replay 迁移")
    a = ap.parse_args()

    if a.reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"已删除 {DB_PATH.name}")

    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    init_state(con, from_replay=not a.full)

    cur = con.cursor()
    print("\n=== 数据库状态 ===")
    for t in ("owned_chara", "owned_card", "owned_cloth", "unlocked_event",
              "story_state", "user_state"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t:16s} {cur.fetchone()[0]:>7} 行")
    cur.execute("SELECT key, value FROM user_state ORDER BY key")
    print("\n=== user_state ===")
    for k, v in cur.fetchall():
        print(f"  {k} = {v}")
    print(f"\n数据库: {DB_PATH} ({DB_PATH.stat().st_size:,} B)")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
