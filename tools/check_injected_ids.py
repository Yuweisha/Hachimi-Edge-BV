"""检查 load/index 里 card_list / cloth_list / chara_list 的 ID 是否都存在于 master，
以及 trained_chara 引用的 card_id 是否有效 —— 用于排查「强化编成」软死。"""
import json
import sqlite3
import struct
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"

b = REPLAY.read_bytes()
n = struct.unpack_from("<I", b, 4)[0]
off = 8
li = None
for _ in range(n):
    a, d, dl = struct.unpack_from("<III", b, off)
    off += 12
    data = b[off:off + dl]
    off += dl
    if d == 1307450:
        li = data
        break

v = msgpack.unpackb(li, raw=False, strict_map_key=False, unicode_errors="replace")
ld = v["data"]

con = sqlite3.connect(MDB)
cur = con.cursor()

# 有效集合
cur.execute("SELECT id FROM card_data")
valid_cards = {r[0] for r in cur.fetchall()}
cur.execute("SELECT id FROM dress_data")
valid_dress = {r[0] for r in cur.fetchall()}
cur.execute("SELECT id FROM chara_data")
valid_chara = {r[0] for r in cur.fetchall()}
con.close()

print(f"master: card_data={len(valid_cards)}, dress_data={len(valid_dress)}, chara_data={len(valid_chara)}")

# card_list
cl = ld.get("card_list", [])
bad_cards = [x.get("card_id") for x in cl if x.get("card_id") not in valid_cards]
print(f"\ncard_list: {len(cl)} 条")
print(f"  无效 card_id: {len(bad_cards)}")
if bad_cards:
    print(f"    前 20: {bad_cards[:20]}")

# cloth_list
cloth = ld.get("cloth_list", [])
bad_cloth = [x.get("cloth_id") for x in cloth if x.get("cloth_id") not in valid_dress]
print(f"cloth_list: {len(cloth)} 条")
print(f"  无效 cloth_id: {len(bad_cloth)}")
if bad_cloth:
    print(f"    前 20: {bad_cloth[:20]}")

# chara_list
chara = ld.get("chara_list", [])
bad_chara = [x.get("chara_id") for x in chara if x.get("chara_id") not in valid_chara]
print(f"chara_list: {len(chara)} 条")
print(f"  无效 chara_id: {len(bad_chara)}")
if bad_chara:
    print(f"    前 20: {bad_chara[:20]}")

# trained_chara 引用
tc = ld.get("trained_chara", [])
bad_tc = [x.get("card_id") for x in tc if x.get("card_id") not in valid_cards]
print(f"trained_chara: {len(tc)} 条")
print(f"  无效 card_id: {len(bad_tc)}")
if bad_tc:
    print(f"    前 20: {bad_tc[:20]}")

# 检查 card_list 里是否有重复
from collections import Counter
dup = [k for k, c in Counter(x.get("card_id") for x in cl).items() if c > 1]
print(f"\ncard_list 重复 card_id: {len(dup)} {dup[:10]}")
dup2 = [k for k, c in Counter(x.get("chara_id") for x in chara).items() if c > 1]
print(f"chara_list 重复 chara_id: {len(dup2)} {dup2[:10]}")
