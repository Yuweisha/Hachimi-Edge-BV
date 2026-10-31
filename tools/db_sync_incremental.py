"""从最新 master.mdb 增量同步到 offline.db。

游戏把数据目录迁到了 _Data/Persistent，master.mdb 也更新了：
  chara_data  +1（9052 未实装，跳过）
  card_data   +1
  dress_data  +4
  single_mode_story_data +121
  support_card_data +3
  jukebox/live +1（music_id 1195）
  gacha_available +1,564

同步内容：
  owned_card    补 master 全部卡（含换皮育成卡）
  owned_cloth   补 master 全部服装
  unlocked_event 补 master 全部 gallery 事件
  card_pool/gacha_pool 重新导入（新卡池）

用法：
  python db_sync_incremental.py
  python db_sync_incremental.py --dry-run
"""
from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

DB = Path(r"C:/Users/Schwarz/uma_replay/offline.db")
MDB = (r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/"
       r"UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
    now = int(time.time())
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    # master 权威数据
    cards = mc.execute("SELECT id, default_rarity FROM card_data").fetchall()
    dresses = [r[0] for r in mc.execute("SELECT id FROM dress_data").fetchall()]
    events = mc.execute(
        "SELECT story_id, card_chara_id FROM single_mode_story_data "
        "WHERE gallery_flag=1").fetchall()
    support = [r[0] for r in mc.execute("SELECT id FROM support_card_data").fetchall()]
    music = [r[0] for r in mc.execute(
        "SELECT music_id FROM jukebox_music_data WHERE is_hidden=0").fetchall()]
    gacha = mc.execute(
        "SELECT gacha_id, card_id, card_type, rarity FROM gacha_available").fetchall()
    mc.close()

    print(f"master: card={len(cards)} dress={len(dresses)} "
          f"event={len(events)} support={len(support)} music={len(music)} gacha={len(gacha):,}")

    con = sqlite3.connect(str(DB), timeout=10)
    cur = con.cursor()

    before = {
        "owned_card": cur.execute("SELECT COUNT(*) FROM owned_card").fetchone()[0],
        "owned_cloth": cur.execute("SELECT COUNT(*) FROM owned_cloth").fetchone()[0],
        "unlocked_event": cur.execute("SELECT COUNT(*) FROM unlocked_event").fetchone()[0],
        "card_pool": cur.execute("SELECT COUNT(*) FROM card_pool").fetchone()[0],
        "gacha_pool": cur.execute("SELECT COUNT(*) FROM gacha_pool").fetchone()[0],
    }
    print(f"\n改前: {before}")

    if a.dry_run:
        print("\n[dry-run] 不写入")
        con.close()
        return 0

    # 1) 卡：不自动扩充 owned_card
    #    客户端 dat/ 资源不全，card_list 超过 181 张会卡 60%。
    #    新卡只能一张一张试（加一张 -> 重启 -> 能进就是有资源）。
    #    card_pool / gacha_pool 仍然全量同步（抽卡用，不影响加载）。
    print(f"  owned_card 保持 {cur.execute('SELECT COUNT(*) FROM owned_card').fetchone()[0]} 张"
          f"（不自动加卡，客户端资源上限）")

    # 2) 服装
    for did in dresses:
        cur.execute("INSERT OR IGNORE INTO owned_cloth(cloth_id) VALUES (?)", (did,))

    # 3) 事件
    for sid, cid in events:
        cur.execute(
            "INSERT OR IGNORE INTO unlocked_event(story_id, chara_id, unlocked_at, new_flag) "
            "VALUES (?,?,?,0)", (sid, cid, ts))

    # 4) card_pool（角色卡 + 支援卡）
    cur.execute("DELETE FROM card_pool")
    rows = []
    for cid, rar in cards:
        if rar in (1, 2, 3):
            rows.append((1, cid, rar))
    mc2 = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
    for sid, rar in mc2.execute("SELECT id, rarity FROM support_card_data").fetchall():
        if rar in (1, 2, 3):
            rows.append((2, sid, rar))
    mc2.close()
    cur.executemany(
        "INSERT OR REPLACE INTO card_pool(card_type, card_id, rarity) VALUES (?,?,?)", rows)

    # 5) gacha_pool
    cur.execute("DELETE FROM gacha_pool")
    cur.executemany(
        "INSERT OR REPLACE INTO gacha_pool(gacha_id, card_id, card_type, rarity) "
        "VALUES (?,?,?,?)", gacha)

    # 6) meta 记录
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('sync_at', ?)", (ts,))
    cur.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('master_music_count', ?)",
                (str(len(music)),))
    con.commit()

    after = {
        "owned_card": cur.execute("SELECT COUNT(*) FROM owned_card").fetchone()[0],
        "owned_cloth": cur.execute("SELECT COUNT(*) FROM owned_cloth").fetchone()[0],
        "unlocked_event": cur.execute("SELECT COUNT(*) FROM unlocked_event").fetchone()[0],
        "card_pool": cur.execute("SELECT COUNT(*) FROM card_pool").fetchone()[0],
        "gacha_pool": cur.execute("SELECT COUNT(*) FROM gacha_pool").fetchone()[0],
    }
    con.close()

    print(f"\n改后: {after}")
    print("\n差异:")
    for k in before:
        d = after[k] - before[k]
        if d:
            print(f"  {k:16s} {before[k]:>8,} -> {after[k]:>8,}  ({d:+,})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
