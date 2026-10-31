"""dump 大表前面的完整内存布局，确定 CodeRegistration 结构。"""
from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes
from pathlib import Path

DLL_PATH = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_rebased.dll"
IMAGE_BASE = 0x180000000
TABLE_RVA = 0x69A3ED8      # 大表起始（运行时扫到的）
COUNT = 201175

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
DONT_RESOLVE_DLL_REFERENCES = 0x00000001

SECTIONS = {
    ".text":  (0x00001000, 0x490000),
    "il2cpp": (0x00491000, 0x5E1F000),
    ".rdata": (0x062B0000, 0x1344000),
    ".data":  (0x075F4000, 0x384E000),
}
CODE_RANGES = [(IMAGE_BASE + SECTIONS[n][0], IMAGE_BASE + SECTIONS[n][0] + SECTIONS[n][1])
               for n in (".text", "il2cpp")]


def is_code(v: int) -> bool:
    return any(lo <= v < hi for lo, hi in CODE_RANGES)


def main():
    h = k32.LoadLibraryExW(DLL_PATH, None, DONT_RESOLVE_DLL_REFERENCES)
    if not h:
        print("加载失败", ctypes.get_last_error())
        return
    base = int(h)
    table_va = base + TABLE_RVA
    print(f"镜像 0x{base:X}  大表 VA=0x{table_va:X}  count={COUNT:,}\n")

    print("=== 大表前 0x100 字节（u32 视图，偏移相对大表）===")
    for k in range(-64, 0, 4):
        va = table_va + k
        v = ctypes.c_uint32.from_address(va).value
        mark = ""
        if 100_000 <= v <= 400_000:
            mark = "  ← 可能是 count"
        print(f"  {k:+4d} (0x{va:X}): {v:>12,}{mark}")

    print("\n=== 大表前 0x100 字节（u64 视图，只有代码指针才显示）===")
    for k in range(-64, 0, 8):
        va = table_va + k
        v = ctypes.c_uint64.from_address(va).value
        if is_code(v):
            print(f"  {k:+4d} (0x{va:X}): 0x{v:016X}  ← 代码指针")

    print("\n=== 大表前 0x100 字节的原始 hex ===")
    raw = bytes((ctypes.c_ubyte * 0x100).from_address(table_va - 0x80))
    for i in range(0, 0x100, 16):
        chunk = raw[i:i+16]
        print(f"  -0x{0x80-i:02X}: {chunk.hex(' ')}")

    # 验证大表本身
    print(f"\n=== 大表验证 ===")
    ok = 0
    bad = 0
    for k in range(100):
        v = ctypes.c_uint64.from_address(table_va + k*8).value
        if is_code(v):
            ok += 1
        else:
            bad += 1
            if bad <= 3:
                print(f"  第 {k} 个不是代码指针: 0x{v:X}")
    print(f"  前 100 个: {ok} 个代码指针")


if __name__ == "__main__":
    main()
