"""对比各备份里 character_story_data_list 的原始状态，找出「原本已读完」的角色。"""
import struct
from collections import defaultdict
from pathlib import Path

import msgpack

D = Path(r"C:/Users/Schwarz/uma_replay")
BACKUPS = [
    "replay.bin.bak_fullunlock",   # 第一次全量注入之前
    "replay.bin.bak_chara_173",    # chara_list 补全后
    "replay.bin.bak_profile",      # profile 补全前
    "replay.bin.bak_epfix",        # episode_id 修正前
    "replay.bin.bak_training",     # training_num 对齐前
    "replay.bin",                  # 当前
]


def load_index_items(p: Path):
    b = p.read_bytes()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    out = {}
    for _ in range(n):
        a, d, dl = struct.unpack_from("<III", b, off)
        off += 12
        data = b[off:off + dl]
        off += dl
        try:
            v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
            if isinstance(v, dict) and "character_story_data_list" in v.get("data", {}):
                out[d] = v
        except Exception:
            pass
    return out


for name in BACKUPS:
    p = D / name
    if not p.exists():
        print(f"{name}: 不存在")
        continue
    items = load_index_items(p)
    if not items:
        print(f"{name}: 没有 load/index")
        continue
    decl = max(items)
    cs = items[decl]["data"]["character_story_data_list"]
    # 按角色统计 episode_id 数量
    g = defaultdict(set)
    for x in cs:
        g[x.get("chara_id", -1)].add(x.get("episode_id"))
    full = [c for c, eps in g.items() if len(eps) >= 7]
    print(f"\n{name}  (declared={decl})")
    print(f"  character_story_data_list: {len(cs)} 条, {len(g)} 个角色")
    print(f"  7 集齐全的角色: {len(full)} 个 {sorted(full)[:10]}")
    print(f"  1001 的 episode_id: {sorted(g.get(1001, []))}")
    # 抽样：1002
    print(f"  1002 的 episode_id: {sorted(g.get(1002, []))}")
