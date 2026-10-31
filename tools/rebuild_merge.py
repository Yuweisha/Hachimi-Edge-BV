"""增量重建 replay.bin：只添加/更新当前会话抓到的接口，旧条目全部保留。

映射方式：path_declared.json 的路径（a/b/c）↔ 文件名（NNNN_a_b_c.msgpack）。
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import struct
import sys
import time
from pathlib import Path

GD = Path(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn")
REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")


def load_replay(path: Path) -> dict[int, bytes]:
    if not path.exists():
        return {}
    b = path.read_bytes()
    if len(b) < 8 or b[:4] != b"RPLY":
        return {}
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items: dict[int, bytes] = {}
    for _ in range(n):
        if off + 12 > len(b):
            break
        _a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        if off + dl > len(b):
            break
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


def path_by_length(length: int, decl: dict[str, int]) -> str | None:
    """按数据长度反查路径（插件落盘的文件名不可靠，只能靠长度）。"""
    hits = [p for p, v in decl.items() if v == length]
    if len(hits) == 1:
        return hits[0]
    return None


def main() -> int:
    sess = Path(sys.argv[1]) if len(sys.argv) > 1 else newest_session()
    if not sess:
        print("找不到带 *.msgpack 的会话目录")
        return 1
    files = sorted(glob.glob(str(sess / "*.msgpack")))
    if not files:
        print("该目录没有 *.msgpack")
        return 1
    print(f"会话目录: {sess}")
    print(f"抓到 {len(files)} 个 msgpack")

    cur_decl: dict[str, int] = {}
    if DECL.exists():
        try:
            cur_decl = json.loads(DECL.read_text(encoding="utf-8"))
        except Exception:
            pass
    known_paths = list(cur_decl.keys())

    old = load_replay(REPLAY)
    print(f"旧 replay.bin: {len(old)} 条")

    if REPLAY.exists():
        bak = REPLAY.with_name(f"replay.bin.bak_merge_{time.strftime('%H%M%S')}")
        shutil.copy(REPLAY, bak)
        print(f"已备份 -> {bak.name}")

    added = updated = skipped = 0
    new_decl: dict[str, int] = dict(cur_decl)

    for f in files:
        stem = Path(f).stem
        data = Path(f).read_bytes()
        api = path_by_length(len(data), cur_decl)
        if api is None:
            # 长度也对不上：退回文件名匹配
            body = stem.split("_", 1)[-1]
            hits = [p for p in known_paths if p.replace("/", "_") == body]
            api = hits[0] if len(hits) == 1 else None
        if api is None:
            # 匹配不到已知路径：这是本次新见到的接口
            # 用响应里的顶层 key 或文件名登记，declared 取数据长度
            api = stem.split("_", 1)[-1]
            if api.startswith("resp"):
                api = f"unknown/{api}"
            print(f"  [新接口] {api}  declared={len(data)}")
            new_decl[api] = len(data)
            decl = len(data)
        else:
            decl = cur_decl[api]
        if decl in old:
            # 已有条目：一律保留旧数据（含手工注入的金币/剧情等）
            skipped += 1
            continue
        added += 1
        old[decl] = data

    save_replay(REPLAY, old)
    print(f"合并结果: {len(old)} 条, {REPLAY.stat().st_size} B（新增 {added}，更新 {updated}，跳过 {skipped}）")

    DECL.write_text(json.dumps(new_decl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"path_declared: {len(new_decl)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
