import glob
import os
import msgpack
import sqlite3
from collections import defaultdict

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"

f = max([x for x in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
         if os.path.getsize(x) == 1213518], key=os.path.getmtime)
d = msgpack.unpackb(open(f, "rb").read(), raw=False, strict_map_key=False)["data"]
rel = {x["id"] for x in d["released_episode_data_array"]}

c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
# 每个活动 -> 各集 story_id / episode_index_id
rows = c.execute(
    "SELECT story_event_id, episode_index_id, story_id_1 FROM story_event_story_data ORDER BY story_event_id, episode_index_id"
).fetchall()

by_ev = defaultdict(list)
for ev, epi, sid in rows:
    by_ev[ev].append((epi, sid))

print("活动 -> 已解锁集数（按 story_id 命中 released）")
for ev in sorted(by_ev)[:14]:
    eps = by_ev[ev]
    hit_sid = sum(1 for _, sid in eps if sid in rel)
    hit_epi = sum(1 for epi, _ in eps if epi in rel)
    print(f"  活动 {ev}: 共{len(eps)}集, story_id命中={hit_sid}, episode_index命中={hit_epi}")
