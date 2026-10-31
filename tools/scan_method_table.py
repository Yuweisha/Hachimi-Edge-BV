"""在 .data 段找大块连续代码指针（methodPointers 表，35 万个指针 = 2.8 MB）。

找到后，前面 4 字节就是 methodPointersCount，
再往前找 CodeRegistration 结构起点。
"""
from __future__ import annotations

import struct
from pathlib import Path

DLL = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_rebased.dll")
IMAGE_BASE = 0x180000000

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
    data = DLL.read_bytes()
    dstart, dsize = SECTIONS[".data"]
    seg = data[dstart:dstart + dsize]
    total = len(seg)

    print(f".data 段 0x{dstart:X} ~ 0x{dstart+dsize:X} ({dsize/1024/1024:.1f} MB)")
    print("找连续代码指针区（>= 1000 个，即 8 KB）...\n")

    runs = []
    i = 0
    while i < total - 8:
        v = struct.unpack_from("<Q", seg, i)[0]
        if is_code(v):
            # 扩展
            j = i
            while j < total - 8:
                v2 = struct.unpack_from("<Q", seg, j)[0]
                if is_code(v2):
                    j += 8
                else:
                    break
            n = (j - i) // 8
            if n >= 1000:
                runs.append((dstart + i, n, v))
            i = j
        else:
            i += 8

    print(f"找到 {len(runs)} 个 >=1000 的连续区：")
    for off, n, first in runs:
        mb = n * 8 / 1024 / 1024
        print(f"  文件 0x{off:X}  {n:,} 个指针 ({mb:.2f} MB)  首=0x{first:X}")

    # 对最大的几个，检查前面 4 字节（可能是 count）
    print("\n=== 检查每个区前面的计数 ===")
    for off, n, first in sorted(runs, key=lambda x: -x[1])[:5]:
        for back in (4, 8, 16):
            if off - back < 0:
                continue
            cnt = struct.unpack_from("<I", data, off - back)[0]
            match = "★" if abs(cnt - n) < 100 else ""
            print(f"  0x{off:X} 区({n:,})  前 {back} 字节 u32={cnt:,}  {match}")

    # 直接找 35 万附近的计数
    print("\n=== 直接搜 count ≈ 350000 的 u32（在整个 .data）===")
    found = 0
    for i in range(0, total - 12, 4):
        v = struct.unpack_from("<I", seg, i)[0]
        if 340000 <= v <= 360000:
            # 后面 8 字节应该是指针
            ptr = struct.unpack_from("<Q", seg, i + 8)[0] if i + 16 <= total else 0
            if IMAGE_BASE + dstart <= ptr < IMAGE_BASE + dstart + dsize:
                print(f"  文件 0x{dstart+i:X}  count={v:,}  next=0x{ptr:X}")
                found += 1
                if found > 10:
                    break
    if not found:
        print("  没找到")


if __name__ == "__main__":
    main()
