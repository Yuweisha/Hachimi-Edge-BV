"""在会话目录里找 453 字节的 msgpack，按内容特征识别 team_stadium/index。"""
import glob
import json
import os
from pathlib import Path

import msgpack

GD = Path(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn")
sessions = sorted(glob.glob(str(GD / "hachimi" / "http" / "*")), key=os.path.getmtime, reverse=True)

hits = []
for sess in sessions:
    for f in glob.glob(os.path.join(sess, "*.msgpack")):
        if os.path.getsize(f) != 453:
            continue
        try:
            v = msgpack.unpackb(Path(f).read_bytes(), raw=False, strict_map_key=False,
                                unicode_errors="replace")
        except Exception:
            continue
        d = v.get("data", {})
        keys = list(d.keys()) if isinstance(d, dict) else []
        hits.append((os.path.basename(sess), os.path.basename(f), keys))

print(f"找到 {len(hits)} 个 453 字节的 msgpack:")
for sess, name, keys in hits:
    print(f"  {sess}/{name}")
    print(f"     data keys = {keys}")

print("\n=== 判定 ===")
for sess, name, keys in hits:
    if "team_stadium_user" in keys or "team_stadium_race_status" in keys or "team_data_array" in keys:
        print(f"  ★ team_stadium/index = {sess}/{name}")
    elif "auth_key" in keys:
        print(f"  ✗ 登录响应 = {sess}/{name}")

# 对照 master 里 team_stadium 应有字段
print("\n=== load/index 里 team_stadium 相关字段 ===")
print("  team_stadium_race_status, team_stadium_user, team_data_array")
