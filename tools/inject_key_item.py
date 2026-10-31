"""给 load/index 注入钥匙道具（item_id=190, 9999 个）。

钥匙规格（实测）：
  item_id = 190
  item_category = 172
  用途：解锁育成事件图鉴里的剧情（消耗 1 把 / 1 条）

同时确保其他常用道具也在：
  59   = 金币
  13   = ？（之前误判，实际不是金币）
  190  = 钥匙

改完同步 path_declared。
"""
import json
import shutil
import struct
import time
from pathlib import Path

import msgpack

REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")

KEY_ITEM_ID = 190
KEY_COUNT = 9999


def load_replay(path: Path) -> dict[int, bytes]:
    b = path.read_bytes()
    assert b[:4] == b"RPLY", "不是 RPLY 格式"
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


def main() -> int:
    decl = json.loads(DECL.read_text(encoding="utf-8"))
    li_decl = decl.get("load/index")
    if not li_decl:
        print("path_declared 里没有 load/index")
        return 1

    items = load_replay(REPLAY)
    raw = items.get(li_decl)
    if raw is None:
        print(f"replay.bin 里没有 load/index (declared={li_decl})")
        # 尝试找出带 character_story_data_list 的那条
        for d, data in items.items():
            try:
                v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
                if isinstance(v, dict) and "character_story_data_list" in v.get("data", {}):
                    raw = data
                    li_decl = d
                    print(f"  改用 declared={d}")
                    break
            except Exception:
                pass
        if raw is None:
            return 1

    v = msgpack.unpackb(raw, raw=False, strict_map_key=False, unicode_errors="replace")
    dd = v.get("data", {})
    items_list = dd.get("item_list")
    if not isinstance(items_list, list):
        print("load/index 里没有 item_list")
        return 1

    print(f"改前 item_list: {len(items_list)} 条")

    # 找钥匙
    found = None
    for it in items_list:
        if isinstance(it, dict) and it.get("item_id") == KEY_ITEM_ID:
            found = it
            break

    if found is not None:
        old = found.get("number")
        found["number"] = KEY_COUNT
        print(f"  钥匙(item {KEY_ITEM_ID}): {old} -> {KEY_COUNT}")
    else:
        items_list.append({"item_id": KEY_ITEM_ID, "number": KEY_COUNT})
        print(f"  新增钥匙(item {KEY_ITEM_ID}): {KEY_COUNT}")

    # 顺便核对金币
    for it in items_list:
        if isinstance(it, dict) and it.get("item_id") == 59:
            print(f"  金币(item 59): {it.get('number')}")

    # 时间字段推远（避免「日期已变更」提示）
    now = int(time.time())
    hdrs = v.get("data_headers")
    if isinstance(hdrs, dict):
        hdrs["servertime"] = now

    new = msgpack.packb(v, use_bin_type=True)
    print(f"\n重编码 {len(raw)} -> {len(new)} B ({len(new) - len(raw):+d})")

    # 备份
    bak = REPLAY.with_name(f"replay.bin.bak_keys_{time.strftime('%H%M%S')}")
    shutil.copy(REPLAY, bak)
    print(f"已备份 -> {bak.name}")

    items.pop(li_decl, None)
    items[len(new)] = new
    save_replay(REPLAY, items)

    decl["load/index"] = len(new)
    DECL.write_text(json.dumps(decl, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"replay.bin: {len(items)} 条")
    print(f"path_declared load/index = {len(new)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
