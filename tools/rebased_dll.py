"""把内存 dump 的 DLL 重定位成标准 ImageBase 形式。

内存 dump 的指针是运行时绝对地址（0x7ff9f2a00000+），
Il2CppDumper / Ghidra 需要 0x180000000 相对的形式。

做法：扫描所有 8 字节对齐位置，把落在 [dump_base, dump_base+size) 的值
改写为 0x180000000 + (v - dump_base)。
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

SRC = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll")
DST = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_rebased.dll")
DUMP_BASE = 0x7FF9F2A00000
NEW_BASE = 0x180000000
MAX_SIZE = 0x0C000000  # 192 MB


def main():
    data = bytearray(SRC.read_bytes())
    total = len(data)
    print(f"源文件 {total:,} B")
    print(f"dump 基址 0x{DUMP_BASE:x} → 新基址 0x{NEW_BASE:x}")

    limit = DUMP_BASE + MAX_SIZE
    patched = 0
    # 按 8 字节对齐扫描
    for off in range(0, total - 8, 8):
        v = struct.unpack_from("<Q", data, off)[0]
        if DUMP_BASE <= v < limit:
            nv = NEW_BASE + (v - DUMP_BASE)
            struct.pack_into("<Q", data, off, nv)
            patched += 1

    print(f"改写 {patched:,} 个指针")
    DST.write_bytes(data)
    print(f"已写入 {DST}  ({DST.stat().st_size:,} B)")

    # 验证
    check = DST.read_bytes()
    rt = img = 0
    for off in range(0, min(len(check), 0x1000000) - 8, 8):
        v = struct.unpack_from("<Q", check, off)[0]
        if 0x7FF000000000 <= v <= 0x7FFFFFFFFFFFF:
            rt += 1
        elif NEW_BASE <= v < NEW_BASE + MAX_SIZE:
            img += 1
    print(f"\n验证（前 16MB）：运行时地址 {rt} 个，新基址形式 {img} 个")


if __name__ == "__main__":
    main()
