"""动态生成 trained_chara/load 响应。

殿堂（名鉴）点开某匹马时，客户端会请求 trained_chara/load，参数里带要看的 id。
离线库里从来没录到这个接口，服务器回空占位，客户端解析失败就报「无法读取数据」。

这里从 load/index.trained_chara 按 id 取记录返回。

响应结构照 load/index 里的单条记录（53 字段），外面包一层。
"""
from __future__ import annotations

import sqlite3


def _all_trained(con: sqlite3.Connection) -> list[dict]:
    import msgpack

    r = con.execute("SELECT data FROM response_cache WHERE path='load/index'").fetchone()
    if not r:
        return []
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    return (obj.get("data") or {}).get("trained_chara") or []


def _ids_from_req(req: dict | None) -> list[int]:
    """从请求里挖出要加载的 id（参数名不确定，几种都试）。"""
    if not req:
        return []
    out: list[int] = []
    for key in ("trained_chara_id_array", "trained_chara_id_list", "trained_chara_id"):
        v = req.get(key)
        if isinstance(v, int):
            out.append(v)
        elif isinstance(v, list):
            out.extend(x for x in v if isinstance(x, int))
    # 兜底：扫所有 int 值里像 id 的
    if not out:
        for k, v in req.items():
            if k in ("viewer_id", "device", "device_id"):
                continue
            if isinstance(v, int) and 1 <= v <= 100000:
                out.append(v)
    return out


def build_trained_chara_load(con: sqlite3.Connection, req: dict | None):
    """返回 (data_dict, note_str)。"""
    tc = _all_trained(con)
    if not tc:
        return None, "库里没有 load/index.trained_chara"

    by_id = {t.get("trained_chara_id"): t for t in tc}
    want = _ids_from_req(req)

    picked = []
    for tid in want:
        t = by_id.get(tid)
        if t:
            picked.append(t)
    if not picked:
        # 拿不到 id 就返回第一匹，至少结构合法
        picked = tc[:1]
        note = f"请求里没解析出 id（{want[:5]}），返回第一匹 {picked[0].get('trained_chara_id')}"
    else:
        note = f"按 id {want[:5]} 返回 {len(picked)} 匹"

    data = {
        "trained_chara_array": picked,
        "trained_chara": picked[0] if len(picked) == 1 else None,
    }
    return data, note
