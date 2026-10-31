"""从 GOLDEN 基线还原 replay.bin / path_declared / locked_paths。

当在线录制或误操作把注入数据覆盖掉时用这个恢复。
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

D = Path(r"C:/Users/Schwarz/uma_replay")
PAIRS = [
    ("replay.bin", "replay.bin.GOLDEN"),
    ("path_declared.json", "path_declared.json.GOLDEN"),
    ("locked_paths.json", "locked_paths.json.GOLDEN"),
]


def main() -> int:
    missing = [g for _, g in PAIRS if not (D / g).exists()]
    if missing:
        print(f"缺少 GOLDEN 文件: {missing}")
        return 1

    stamp = time.strftime("%H%M%S")
    for cur, gold in PAIRS:
        cur_p, gold_p = D / cur, D / gold
        if cur_p.exists():
            bak = D / f"{cur}.before_restore_{stamp}"
            shutil.copy(cur_p, bak)
            print(f"  备份 {cur} -> {bak.name}")
        shutil.copy(gold_p, cur_p)
        print(f"  还原 {cur}  <- {gold}  ({cur_p.stat().st_size} B)")

    print("\n还原完成。重启服务器让它重新读表。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
