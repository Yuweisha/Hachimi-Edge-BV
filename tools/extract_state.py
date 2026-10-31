"""从 load/index 提取「世界状态」骨架。

state 是服务端唯一数据源；所有接口响应都从它注入。
只提取会变的、界面会读的字段，其余原样保留在模板里。
"""
from __future__ import annotations

import glob
import json
import os
import sys

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
OUT = r"C:/Users/Schwarz/uma_replay/state.json"


def newest(size: int) -> str | None:
    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if os.path.getsize(f) == size]
    return max(cands, key=os.path.getmtime) if cands else None


def main() -> int:
    # 用最新一次会话的 load/index
    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if 1_200_000 < os.path.getsize(f) < 1_300_000]
    if not cands:
        print("找不到 load/index")
        return 1
    f = max(cands, key=os.path.getmtime)
    print("源:", f)
    v = msgpack.unpackb(open(f, "rb").read(), raw=False, strict_map_key=False)
    d = v.get("data", {})

    state = {
        "_meta": {
            "viewer_id": v.get("data_headers", {}).get("viewer_id"),
            "servertime": v.get("data_headers", {}).get("servertime"),
            "source": os.path.basename(f),
        },
        "user_info": d.get("user_info", {}),
        "coin_info": d.get("coin_info", {}),
        "tp_info": d.get("tp_info", {}),
        "rp_info": d.get("rp_info", {}),
        "item_list": d.get("item_list", []),
        "trained_chara": d.get("trained_chara", []),
        "support_card_list": d.get("support_card_list", []),
        "mission_list": d.get("mission_list", []),
    }

    # 统计
    print("\n=== state 概览 ===")
    for k in ("user_info", "coin_info", "tp_info", "rp_info"):
        s = state[k]
        if isinstance(s, dict):
            print(f"  {k}: {list(s.keys())[:8]}")
    print(f"  item_list: {len(state['item_list'])} 项")
    print(f"  trained_chara: {len(state['trained_chara'])} 只")
    print(f"  support_card_list: {len(state['support_card_list'])} 张")
    print(f"  mission_list: {len(state['mission_list'])} 条")

    # 金币/石头
    for it in state["item_list"]:
        if isinstance(it, dict) and it.get("item_id") in (13, 14, 15, 16):
            print(f"  item {it.get('item_id')}: {it.get('number')}")
    print(f"  coin_info: {state['coin_info']}")

    # 全量 dump（可能很大，单独存）
    big = r"C:/Users/Schwarz/uma_replay/load_index_template.msgpack"
    open(big, "wb").write(open(f, "rb").read())
    print(f"\n模板已存: {big} ({os.path.getsize(big)} B)")

    # state 精简版（只存会变的部分，避免几十 MB）
    slim = {
        "_meta": state["_meta"],
        "user_info": state["user_info"],
        "coin_info": state["coin_info"],
        "tp_info": state["tp_info"],
        "rp_info": state["rp_info"],
        "item_list": state["item_list"],
        "counts": {
            "trained_chara": len(state["trained_chara"]),
            "support_card_list": len(state["support_card_list"]),
            "mission_list": len(state["mission_list"]),
        },
    }
    json.dump(slim, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"state 已写: {OUT} ({os.path.getsize(OUT)} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
