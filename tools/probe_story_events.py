import sqlite3, glob, os, msgpack

M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
rows = c.execute(
    "SELECT id, story_event_id, episode_index_id, story_type_1, story_id_1, story_type_2, story_id_2 "
    "FROM story_event_story_data ORDER BY id LIMIT 12"
).fetchall()
print("story_event_story_data 样例:")
for r in rows:
    print("  ", r)

cnt = c.execute(
    "SELECT story_event_id, COUNT(*) FROM story_event_story_data GROUP BY story_event_id ORDER BY story_event_id"
).fetchall()
print("\n各活动集数:", cnt[:12])

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
cands = [x for x in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
         if os.path.getsize(x) == 1213518]
f = max(cands, key=os.path.getmtime)
d = msgpack.unpackb(open(f, "rb").read(), raw=False, strict_map_key=False)["data"]
rel = {x["id"] for x in d["released_episode_data_array"]}

allrows = c.execute("SELECT story_id_1, story_id_2 FROM story_event_story_data").fetchall()
sids = set()
for a, b in allrows:
    if a:
        sids.add(a)
    if b:
        sids.add(b)
print("\nstory_id 去重:", len(sids), "样例:", sorted(sids)[:10])
print("已解锁中包含的:", len(sids.intersection(rel)), "/", len(sids))
