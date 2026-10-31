"""静态加载 GameAssembly_rebased.dll，在映射后的镜像里扫 CodeRegistration。

用 LoadLibraryExW(DONT_RESOLVE_DLL_REFERENCES) 把 PE 映射到 0x180000000，
这样拿到的是「已按 PE 布局展开」的镜像，可以直接按 RVA 读数据。
不启动游戏，纯静态。
"""
from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes
from pathlib import Path

DLL_PATH = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_rebased.dll"
# 运行时扫到的大表 RVA = 0x69A3ED8，属于 .rdata 段
IMAGE_BASE = 0x180000000

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
DONT_RESOLVE_DLL_REFERENCES = 0x00000001

# 节表（RVA, VSize）
SECTIONS = {
    ".text":  (0x00001000, 0x490000),
    "il2cpp": (0x00491000, 0x5E1F000),
    ".rdata": (0x062B0000, 0x1344000),
    ".data":  (0x075F4000, 0x384E000),
    ".pdata": (0x0AE42000, 0x4C6000),
}
CODE_RANGES = [(IMAGE_BASE + SECTIONS[n][0], IMAGE_BASE + SECTIONS[n][0] + SECTIONS[n][1])
               for n in (".text", "il2cpp")]


def is_code(v: int) -> bool:
    return any(lo <= v < hi for lo, hi in CODE_RANGES)


def main():
    h = k32.LoadLibraryExW(DLL_PATH, None, DONT_RESOLVE_DLL_REFERENCES)
    if not h:
        err = ctypes.get_last_error()
        print(f"LoadLibraryEx 失败 err={err}")
        return
    base = h if isinstance(h, int) else int(h)
    print(f"镜像基址 = 0x{base:X}")
    if base != IMAGE_BASE:
        print(f"警告：基址不是 0x{IMAGE_BASE:X}，需要按实际基址换算")

    dstart, dsize = SECTIONS[".rdata"]
    seg_va = base + dstart
    print(f".rdata 段 VA 0x{seg_va:X} ~ 0x{seg_va + dsize:X} ({dsize/1024/1024:.1f} MB)\n")

    # 在整个 .data 里找「count(>=150000) + ptr + 指向代码」的结构
    print("=== 找 count + 指针 结构 ===")
    hits = 0
    for off in range(0, dsize - 32, 8):
        va = seg_va + off
        cnt = ctypes.c_uint32.from_address(va).value
        if 150_000 <= cnt <= 400_000:
            # 后面 8 字节（对齐）是指针
            ptr = ctypes.c_uint64.from_address(va + 8).value
            if is_code(ptr):
                # 验证前 64 个元素
                ok = 0
                for k in range(64):
                    try:
                        v = ctypes.c_uint64.from_address(ptr + k * 8).value
                    except Exception:
                        break
                    if is_code(v):
                        ok += 1
                if ok >= 60:
                    print(f"  ★ .data+0x{off:07X}  VA=0x{va:X}  count={cnt:,}  "
                          f"ptr=0x{ptr:X}  ({ok}/64 命中)")
                    hits += 1
                    if hits >= 10:
                        break
    if not hits:
        print("  未找到")

    # 反向：找连续 50000+ 代码指针的大块，然后往前找 count
    print("\n=== 找大块连续代码指针（>=50000）===")
    i = 0
    found = 0
    while i < dsize - 8 * 50000:
        va = seg_va + i
        v = ctypes.c_uint64.from_address(va).value
        if is_code(v):
            n = 0
            j = i
            while j < dsize - 8 and n < 400_000:
                vv = ctypes.c_uint64.from_address(seg_va + j).value
                if is_code(vv):
                    n += 1
                    j += 8
                else:
                    break
            if n >= 50000:
                print(f"  大块 @ .data+0x{i:07X}  VA=0x{va:X}  {n:,} 个 ({n*8/1024/1024:.2f} MB)")
                # 往前找 count
                for back in range(4, 64, 4):
                    c = ctypes.c_uint32.from_address(va - back).value
                    if 100_000 <= c <= 400_000:
                        print(f"      -0x{back:X}: u32={c:,}  ← 可能是 count")
                found += 1
                if found >= 5:
                    break
            i = j
        else:
            i += 8
    if not found:
        print("  未找到")

    pass  # 不 FreeLibrary，避免 ctypes 类型问题


if __name__ == "__main__":
    main()
