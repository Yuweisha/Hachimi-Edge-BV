"""解锁全部故事：把 home_story 和 story_event 的所有 id 塞进 released_episode_data_array。

产物：
  uma_replay/unlock/read_info_index.msgpack  （新的 read_info/index 明文）
  uma_replay/unlock/new_declared.txt         （新长度）
"""
from __future__ import annotations

import glob
import os
import sqlite3
import sys

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
M = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
OUTDIR = r"C:/Users/Schwarz/uma_replay/unlock"


def main() -> int:
    os.makedirs(OUTDIR, exist_ok=True)

    # 1. 找最新的 read_info/index 明文
    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if "home_story_data_array" in os.path.basename(f)]
    if not cands:
        print("找不到 read_info/index")
        return 1
    f = max(cands, key=os.path.getmtime)
    print("源:", os.path.basename(f), os.path.getsize(f))

    raw = open(f, "rb").read()
    v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    d = v["data"]

    rel = [x["id"] for x in d["released_episode_data_array"]]
    before = len(rel)
    have = set(rel)

    # 2. 收集所有应该解锁的 id
    want = set()

    # 主页故事
    for x in d.get("home_story_data_array", []):
        want.add(x["id"])

    # 活动剧情（从 master.mdb）
    try:
        c = sqlite3.connect(f"file:{M}?mode=ro", uri=True)
        for (eid,) in c.execute("SELECT DISTINCT episode_index_id FROM story_event_story_data"):
            want.add(eid)
        print("master: story_event_story_data 已读")
    except Exception as e:
        print("master 读取失败:", e)

    # 3. 合并
    add = sorted(want - have)
    merged = sorted(have | want)
    print(f"原有 {before} 条，新增 {len(add)} 条，合并后 {len(merged)} 条")

    # 4. 重建数组（保持原有条目的其它字段，若无则只给 id）
    tmpl = {}
    for x in d["released_episode_data_array"]:
        tmpl[x["id"]] = x
    new_arr = []
    for i in merged:
        new_arr.append(tmpl.get(i, {"id": i}))
    d["released_episode_data_array"] = new_arr

    # 5. 重编码
    out = msgpack.packb(v, use_bin_type=True)
    outpath = os.path.join(OUTDIR, "read_info_index.msgpack")
    open(outpath, "wb").write(out)
    print(f"写出 {outpath} ({len(raw)} -> {len(out)} B)")

    open(os.path.join(OUTDIR, "new_declared.txt"), "w").write(str(len(out)))
    print("新 declared:", len(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
