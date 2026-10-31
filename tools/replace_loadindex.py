"""用新录制的 load/index 替换旧的，并保留注入内容（金币/钥匙/剧情/散步）。

背景：
  资源更新后 load/index 长度会变（1277815 -> 1217043 之类），
  rebuild_merge.py 会当成"新条目"加入，但 path_declared 指向哪个就成了问题。

本脚本：
  1. 在新会话的 load/index 中定位（找含 character_story_data_list 的最大条目）
  2. 从旧 replay.bin 的 load/index 里搬运注入数据：
     - coin_info（fcoin / coin）
     - item_list（金币 59 / 钥匙 190）
     - character_story_data_list（7/7）
     - event_data_array（已解锁事件）
  3. 写入 replay.bin，删掉旧的 load/index 条目，更新 path_declared
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import struct
import time
from pathlib import Path

import msgpack

GD = Path(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn")
REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")

COIN_TOTAL = 100_000_000
KEY_TOTAL = 9999
KEY_ITEM = 190
GOLD_ITEM = 59


def load_replay(path: Path) -> dict[int, bytes]:
    b = path.read_bytes()
    if b[:4] != b"RPLY":
        return {}
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        _a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl
    return items


def save_replay(path: Path, items: dict[int, bytes]) -> None:
    out = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        out += struct.pack("<III", decl, decl, len(data)) + data
    path.write_bytes(out)


def newest_session() -> Path | None:
    dirs = sorted(glob.glob(str(GD / "hachimi" / "http" / "*")), key=os.path.getmtime, reverse=True)
    for d in dirs:
        if os.path.isdir(d) and glob.glob(os.path.join(d, "*.msgpack")):
            return Path(d)
    return None


def is_load_index(v) -> bool:
    return isinstance(v, dict) and "character_story_data_list" in v.get("data", {})


def find_new_load_index(sess: Path):
    """在新会话里找 load/index（最大的含 character_story_data_list 的条目）"""
    best = None
    for f in sorted(sess.glob("*.msgpack"), key=lambda p: p.stat().st_size, reverse=True):
        try:
            data = f.read_bytes()
            v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        except Exception:
            continue
        if is_load_index(v):
            best = (f, data, v)
            break
    return best


def main() -> int:
    decl = json.loads(DECL.read_text(encoding="utf-8"))
    items = load_replay(REPLAY)

    # 旧 load/index
    old_decl = decl.get("load/index")
    old_v = None
    if old_decl and old_decl in items:
        try:
            old_v = msgpack.unpackb(items[old_decl], raw=False, strict_map_key=False,
                                    unicode_errors="replace")
        except Exception:
            old_v = None
    print(f"旧 load/index: declared={old_decl}, 解析={'OK' if old_v else '失败'}")

    sess = newest_session()
    if not sess:
        print("找不到会话目录")
        return 1
    print(f"会话目录: {sess}")

    found = find_new_load_index(sess)
    if not found:
        print("会话目录里没找到新的 load/index")
        return 1
    nf, ndata, nv = found
    print(f"新 load/index: {nf.name} ({len(ndata)} B)")

    # 搬运注入数据
    if old_v and nv:
        od = old_v.get("data", {})
        nd = nv.get("data", {})

        # 1) coin_info
        if isinstance(od.get("coin_info"), dict):
            nd["coin_info"] = {"fcoin": COIN_TOTAL, "coin": COIN_TOTAL}
            print(f"  coin_info -> fcoin={COIN_TOTAL} coin={COIN_TOTAL}")

        # 2) item_list 里补金币 + 钥匙
        il = nd.get("item_list")
        if not isinstance(il, list):
            il = []
            nd["item_list"] = il
        by_id = {it.get("item_id"): it for it in il if isinstance(it, dict)}

        if GOLD_ITEM in by_id:
            by_id[GOLD_ITEM]["number"] = COIN_TOTAL
        else:
            il.append({"item_id": GOLD_ITEM, "number": COIN_TOTAL})
        print(f"  金币(item {GOLD_ITEM}) = {COIN_TOTAL}")

        if KEY_ITEM in by_id:
            by_id[KEY_ITEM]["number"] = KEY_TOTAL
        else:
            il.append({"item_id": KEY_ITEM, "number": KEY_TOTAL})
        print(f"  钥匙(item {KEY_ITEM}) = {KEY_TOTAL}")

        # 3) 剧情 7/7 —— 从旧数据搬（如果旧数据是修复过的）
        old_cs = od.get("character_story_data_list", [])
        new_cs = nd.get("character_story_data_list", [])
        print(f"  character_story_data_list: 旧={len(old_cs)} 新={len(new_cs)}")
        if len(old_cs) > len(new_cs):
            nd["character_story_data_list"] = old_cs
            print(f"    -> 沿用旧数据（{len(old_cs)} 条）")

        # 4) event_data_array —— 保留旧的（含已解锁记录）
        old_ev = od.get("event_data_array", [])
        new_ev = nd.get("event_data_array", [])
        print(f"  event_data_array: 旧={len(old_ev)} 新={len(new_ev)}")
        if old_ev and len(old_ev) >= len(new_ev):
            # 合并：以旧为主，补新的
            seen = {(e.get("chara_id"), e.get("data_id")) for e in old_ev if isinstance(e, dict)}
            merged = list(old_ev)
            for e in new_ev:
                if isinstance(e, dict):
                    k = (e.get("chara_id"), e.get("data_id"))
                    if k not in seen:
                        merged.append(e)
                        seen.add(k)
            nd["event_data_array"] = merged
            print(f"    -> 合并后 {len(merged)} 条")

        # servertime 更新
        hdrs = nv.get("data_headers")
        if isinstance(hdrs, dict):
            hdrs["servertime"] = int(time.time())

    new_data = msgpack.packb(nv, use_bin_type=True)
    print(f"\n重编码 {len(ndata)} -> {len(new_data)} B")

    bak = REPLAY.with_name(f"replay.bin.bak_loadidx_{time.strftime('%H%M%S')}")
    shutil.copy(REPLAY, bak)
    print(f"已备份 -> {bak.name}")

    # 删掉所有旧 load/index 条目（按内容判定）
    removed = []
    for d in list(items.keys()):
        if old_decl and d == old_decl:
            del items[d]
            removed.append(d)
            continue
        try:
            v = msgpack.unpackb(items[d], raw=False, strict_map_key=False, unicode_errors="replace")
            if is_load_index(v):
                del items[d]
                removed.append(d)
        except Exception:
            pass
    print(f"删除旧 load/index 条目: {removed}")

    items[len(new_data)] = new_data
    save_replay(REPLAY, items)

    decl["load/index"] = len(new_data)
    DECL.write_text(json.dumps(decl, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nreplay.bin: {len(items)} 条")
    print(f"path_declared load/index = {len(new_data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
