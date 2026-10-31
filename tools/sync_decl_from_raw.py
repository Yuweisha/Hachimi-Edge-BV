"""从 raw/*.raw 提取「路径 -> declared」，并检查对应明文是否已在 replay.bin。

raw 文件 = base64 文本；解码后 [0:4]=declared（0 表示不压缩，用负值记明文长度）。
"""
from __future__ import annotations

import base64
import json
import struct
from pathlib import Path

import msgpack

RAW = Path(r"C:/Users/Schwarz/uma_replay/raw")
REPLAY = Path(r"C:/Users/Schwarz/uma_replay/replay.bin")
DECL = Path(r"C:/Users/Schwarz/uma_replay/path_declared.json")
LOCKED = Path(r"C:/Users/Schwarz/uma_replay/locked_paths.json")


def load_replay_decls() -> dict[int, bytes]:
    b = REPLAY.read_bytes()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    out = {}
    for _ in range(n):
        a, d, dl = struct.unpack_from("<III", b, off)
        off += 12
        out[d] = b[off:off + dl]
        off += dl
    return out


def main() -> int:
    lib = load_replay_decls()
    print(f"replay.bin: {len(lib)} 个 declared")

    locked = set()
    if LOCKED.exists():
        try:
            data = json.loads(LOCKED.read_text(encoding="utf-8"))
            if isinstance(data, list):
                locked = set(data)
        except Exception:
            pass
    print(f"锁定: {sorted(locked) or '（无）'}")

    cur = json.loads(DECL.read_text(encoding="utf-8")) if DECL.exists() else {}

    found = []
    for f in sorted(RAW.glob("*.raw")):
        rel = f.stem.replace("_", "/")
        try:
            b64 = f.read_bytes().strip()
            raw = base64.b64decode(b64 + b"==" * (4 - len(b64) % 4 if len(b64) % 4 else 0))
        except Exception as e:
            print(f"  {f.name}: base64 失败 {e}")
            continue
        if len(raw) < 4:
            print(f"  {f.name}: 太短 {len(raw)}")
            continue
        decl = struct.unpack_from("<I", raw, 0)[0]
        if decl == 0:
            plain = len(raw) - 36
            key = -plain
            note = f"不压缩，明文 {plain}"
            probe = plain
        else:
            key = decl
            note = f"压缩，明文 {decl}"
            probe = decl
        in_lib = probe in lib
        found.append((rel, key, note, in_lib))
        print(f"  {rel:<42} {note:<22} 库中{'有' if in_lib else '无'}")

    print(f"\n共 {len(found)} 个 raw")
    missing = [x for x in found if not x[3]]
    if missing:
        print(f"库中缺 {len(missing)} 个:")
        for rel, key, note, _ in missing:
            print(f"    {rel}  ({note})")

    # 更新 path_declared（带锁定保护）
    added = changed = 0
    for rel, key, note, in_lib in found:
        if rel in locked:
            print(f"  [锁定] {rel} = {cur.get(rel)}（忽略 {key}）")
            continue
        if rel not in cur:
            cur[rel] = key
            added += 1
        elif cur[rel] != key:
            cur[rel] = key
            changed += 1
    DECL.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\npath_declared: {len(cur)} 条（新增 {added}，更新 {changed}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
