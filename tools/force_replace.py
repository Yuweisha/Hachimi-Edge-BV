"""用新录制的响应替换 replay.bin 里同 declared 的旧条目。

解决 rebuild_merge.py 的盲区：它按 declared 判断"是否已存在"，
长度相同但内容变了（如 start_session 的 resource_version）会被跳过。

用法：
  python force_replace.py 526                                    # 用最新会话的同 declared 替换
  python force_replace.py 526 --session 20261026_152314          # 指定会话
  python force_replace.py --path tool/start_session              # 按路径（查 path_declared 得 declared）
"""
from __future__ import annotations

import argparse
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


def find_file(sess: Path, declared: int) -> Path | None:
    """在会话目录里找长度等于 declared 的 .msgpack"""
    for f in sorted(sess.glob("*.msgpack")):
        if f.stat().st_size == declared:
            return f
    return None


def describe(data: bytes) -> str:
    try:
        v = msgpack.unpackb(data, raw=False, strict_map_key=False, unicode_errors="replace")
        if isinstance(v, dict):
            rc = v.get("response_code")
            dd = v.get("data", {})
            keys = list(dd.keys())[:5] if isinstance(dd, dict) else []
            extra = ""
            if isinstance(dd, dict) and "resource_version" in dd:
                extra = f" resource_version={dd['resource_version']}"
            return f"response_code={rc} data_keys={keys}{extra}"
    except Exception as e:
        return f"（解析失败 {e}）"
    return "（非 dict）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("declared", nargs="?", type=int, default=0)
    ap.add_argument("--session", default=None)
    ap.add_argument("--path", default=None, help="按 API 路径查 declared")
    a = ap.parse_args()

    decl = json.loads(DECL.read_text(encoding="utf-8"))

    declared = a.declared
    if a.path:
        declared = abs(decl.get(a.path, 0))
        if not declared:
            print(f"path_declared 里没有 {a.path}")
            return 1
        print(f"{a.path} -> declared={declared}")

    if not declared:
        print("需要 declared 或 --path")
        return 1

    sess = Path(a.session) if a.session else newest_session()
    if not sess:
        print("找不到会话目录")
        return 1
    print(f"会话目录: {sess}")

    src = find_file(sess, declared)
    if not src:
        print(f"会话目录里没有长度为 {declared} 的 .msgpack")
        return 1

    new_data = src.read_bytes()
    print(f"新数据: {src.name} ({len(new_data)} B)")
    print(f"  {describe(new_data)}")

    items = load_replay(REPLAY)
    old_data = items.get(declared)
    if old_data is None:
        # 直接新增
        print(f"\nreplay.bin 里没有 declared={declared}，直接新增")
    else:
        print(f"\n旧数据 ({len(old_data)} B)")
        print(f"  {describe(old_data)}")
        if old_data == new_data:
            print("\n内容相同，无需替换")
            return 0

    bak = REPLAY.with_name(f"replay.bin.bak_repl_{time.strftime('%H%M%S')}")
    shutil.copy(REPLAY, bak)
    print(f"\n已备份 -> {bak.name}")

    items[declared] = new_data
    save_replay(REPLAY, items)
    print(f"替换完成，replay.bin {len(items)} 条")

    # 校验
    chk = load_replay(REPLAY).get(declared)
    print(f"校验: {'一致' if chk == new_data else '不一致！'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
