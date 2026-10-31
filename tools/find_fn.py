"""从 decompiled.c 里按「运行时方法地址」反查反编译函数体。

原理：
    运行时地址 - GameAssembly 模块基址 = RVA
    decompiled.c 里的地址 = 0x180000000 + RVA

已知样本：
    base   = 0x7ff961b20000
    method = 0x7ff961fb1170   (GetHorseResultDataArray)
    → RVA  = 0x491170
    → 反编译地址 = 0x180491170  →  FUN_180491170

用法：
    python find_fn.py 0x7ff961fb1170 [更多地址...]
    python find_fn.py --base 0x7ff961b20000 0x7ff961fb1170
"""
import argparse
import re
import sys
from pathlib import Path

DECOMP = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/decompiled.c")
IMAGE_BASE = 0x180000000
DEFAULT_BASE = 0x7FF961B20000


def load_index(dec_path: Path) -> dict[int, int]:
    """扫描一遍反编译文件，建立 {反编译地址: 起始行号}。"""
    index: dict[int, int] = {}
    pat = re.compile(rb"^// FUN_([0-9a-fA-F]+) @ 0x([0-9a-fA-F]+)\s*$")
    with dec_path.open("rb") as f:
        for lineno, line in enumerate(f, 1):
            m = pat.match(line)
            if m:
                addr = int(m.group(2), 16)
                index[addr] = lineno
    return index


def read_fn(dec_path: Path, start_line: int, max_lines: int = 120) -> list[str]:
    out = []
    with dec_path.open("r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i < start_line:
                continue
            if i > start_line + max_lines:
                break
            out.append(line.rstrip("\n"))
            # 遇到下一个函数头就停
            if i > start_line and line.startswith("// FUN_") :
                out.pop()
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("addrs", nargs="+", help="运行时方法地址（0x...）")
    ap.add_argument("--base", default=hex(DEFAULT_BASE), help="GameAssembly 运行时基址")
    ap.add_argument("--lines", type=int, default=100, help="每个函数最多打印多少行")
    a = ap.parse_args()

    base = int(a.base, 16)
    print(f"GameAssembly base = {base:#x}")
    print(f"反编译文件 {DECOMP}  ({DECOMP.stat().st_size:,} B)")
    print("建立函数索引中...")
    index = load_index(DECOMP)
    print(f"索引完成：{len(index):,} 个函数\n")

    for s in a.addrs:
        rt = int(s, 16)
        rva = rt - base
        dec_addr = IMAGE_BASE + rva
        print(f"{'='*70}")
        print(f"运行时 {rt:#x}  - base = RVA {rva:#x}  →  反编译 {dec_addr:#x}")
        line = index.get(dec_addr)
        if line is None:
            # 允许 ±0x10 误差（方法指针可能指向 thunk）
            for delta in (0x10, -0x10, 0x20, -0x20, 0x30, -0x30):
                if dec_addr + delta in index:
                    line = index[dec_addr + delta]
                    print(f"  （近似命中 {dec_addr + delta:#x}）")
                    break
        if line is None:
            print("  反编译里找不到这个地址")
            continue
        body = read_fn(DECOMP, line, a.lines)
        for l in body:
            print("  " + l)
        print()


if __name__ == "__main__":
    main()
