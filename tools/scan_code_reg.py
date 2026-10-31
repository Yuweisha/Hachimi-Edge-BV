"""暴力扫描 GameAssembly 的 .data 段，找 Il2CppCodeRegistration / MetadataRegistration。

Crackproof 改了表结构，Il2CppDumper 的启发式扫不到。这里按 v31 的结构特征硬找：
  - CodeRegistration 里有一个 u32 计数 + 紧跟一个指向代码段的指针数组
  - 计数值应该和 metadata 里的方法总数（350215）接近
  - 数组里每个指针应该落在 il2cpp/.text 节范围内

用法：
    python scan_code_reg.py
"""
from __future__ import annotations

import struct
from pathlib import Path

DLL = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_rebased.dll")
IMAGE_BASE = 0x180000000

# 节表（从之前验证结果）
SECTIONS = {
    ".text":  (0x00001000, 0x490000),
    "il2cpp": (0x00491000, 0x5E1F000),
    ".rdata": (0x062B0000, 0x1344000),
    ".data":  (0x075F4000, 0x384E000),
    ".pdata": (0x0AE42000, 0x4C6000),
}

METHOD_COUNT = 350215  # metadata 里的方法总数


def in_code_range(v: int) -> bool:
    """地址是否落在可执行节（.text 或 il2cpp）里。"""
    for name in (".text", "il2cpp"):
        va, vsz = SECTIONS[name]
        if IMAGE_BASE + va <= v < IMAGE_BASE + va + vsz:
            return True
    return False


def main():
    data = DLL.read_bytes()
    dstart, dsize = SECTIONS[".data"]
    print(f".data 段: 文件偏移 0x{dstart:X}, 大小 0x{dsize:X} ({dsize/1024/1024:.1f} MB)")

    # 1) 找 METHOD_COUNT 附近的 u32
    targets = [METHOD_COUNT, METHOD_COUNT - 1, METHOD_COUNT + 1]
    print(f"目标方法数: {targets}")

    hits = []
    chunk = data[dstart:dstart+dsize]
    for i in range(0, len(chunk)-16, 4):
        v = struct.unpack_from("<I", chunk, i)[0]
        if v in targets:
            # 后面 8 字节（对齐到 8）应该是指针
            for pad in (0, 4):
                poff = i + 4 + pad
                if poff + 8 > len(chunk):
                    continue
                ptr = struct.unpack_from("<Q", chunk, poff)[0]
                # 指针应该指向一个地址数组，或者本身就是数组首地址
                if IMAGE_BASE + SECTIONS[".data"][0] <= ptr < IMAGE_BASE + SECTIONS[".data"][0] + dsize:
                    hits.append((dstart + i, v, ptr, pad))
    print(f"\n候选（计数匹配 + 后随 .data 指针）: {len(hits)}")
    for foff, cnt, ptr, pad in hits[:20]:
        print(f"  文件 0x{foff:X}  count={cnt}  next_ptr=0x{ptr:X} (pad={pad})")

    # 2) 对每个候选，验证指针数组里的元素是否落在代码段
    print("\n=== 验证指针数组 ===")
    best = []
    for foff, cnt, ptr, pad in hits:
        arr_off = ptr - IMAGE_BASE  # 转文件偏移（.data 段 RawOff == VA）
        if not (0 <= arr_off < len(data) - 8*8):
            continue
        valid = 0
        total = min(64, cnt)
        for k in range(total):
            v = struct.unpack_from("<Q", data, arr_off + k*8)[0]
            if in_code_range(v):
                valid += 1
        if total > 0 and valid / total > 0.9:
            best.append((foff, cnt, ptr, valid, total))
            print(f"  ★ 文件 0x{foff:X}  count={cnt}  arr=0x{ptr:X}  "
                  f"valid={valid}/{total}")

    if not best:
        print("  没有找到高命中率的候选")

    # 3) 反向做法：直接找「连续 64 个都指向代码段的指针数组」
    print("\n=== 直接找指针数组（连续 64 个都指向代码段）===")
    found = 0
    i = 0
    while i < len(chunk) - 8*64:
        ptr = struct.unpack_from("<Q", chunk, i)[0]
        if in_code_range(ptr):
            ok = 0
            for k in range(64):
                v = struct.unpack_from("<Q", chunk, i + k*8)[0]
                if in_code_range(v):
                    ok += 1
                else:
                    break
            if ok >= 64:
                # 往前找连续起点
                print(f"  文件 0x{dstart+i:X}  连续 {ok}+ 个代码指针  首值=0x{ptr:X}")
                found += 1
                i += 8 * 64
                if found >= 10:
                    break
        i += 8
    if not found:
        print("  没找到")


if __name__ == "__main__":
    main()
