"""从 metadata v31 生成 dump.cs（C# 类结构 + 字段偏移 + 方法 RVA）。

不依赖 Il2CppDumper —— 直接解析 metadata 二进制 + 运行时定位到的 methodPointers 表。

结构（v31）：
  Il2CppTypeDefinition stride 0x58
    +0x00 nameIndex (i32)
    +0x04 namespaceIndex (i32)
    +0x10 byvalTypeIndex / 等
    +0x40 methodStart (u16)
    +0x42 methodCount (u16)
    +0x44 fieldStart (u16)
    +0x46 fieldCount (u16)
  Il2CppMethodDefinition stride 0x24
    +0x00 nameIndex (i32)
    +0x04 declaringType (i32)
    +0x08 returnType (i32)
    +0x0C parameterStart (u32)
    +0x14 token (u32)
    +0x18 flags (u16)
    +0x22 parameterCount (u16)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

META = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/metadata_jp_recovered.dat")
DUMP = Path(r"C:/Users/Schwarz/Hachimi-Edge/docs/_none")  # placeholder
OUT = Path(r"C:/Users/Schwarz/uma_metadata/dump_subset.cs")

TD_STRIDE = 0x58
MD_STRIDE = 0x24

# metadata 头部（v31）：sanity(4) version(4) 然后一组 offset/大小对
# 已知 layout（从 parse_metadata_v31.py 验证过）：
#   +0x00 sanity = 0xFAB11BAF
#   +0x04 version = 31
#   +0x08 stringLiteralOffset
#   ...


class Metadata:
    def __init__(self, path: Path):
        self.blob = path.read_bytes()
        self.strings = self._find_strings()

    def _find_strings(self) -> bytes:
        """字符串池：从第一个合法字符串区开始。简化处理：整块 blob 当候选。"""
        return self.blob

    def string_at(self, offset: int) -> str:
        if offset < 0 or offset >= len(self.blob):
            return ""
        end = self.blob.find(b"\x00", offset)
        if end < 0:
            end = offset + 64
        return self.blob[offset:end].decode("utf-8", "replace")


def find_tables(blob: bytes):
    """在 metadata 里定位 typeDefinitions / methodDefinitions 表。

    特征：typeDefinitions 是一串 0x58 步长的记录，第一条通常是 <Module>。
    """
    n = len(blob)
    results = {}

    # 暴力扫：找「看起来像 typeDefinitions 起点」的位置
    # 条件：连续 8 条记录的 methodCount <= 3000 且 fieldCount <= 3000
    for start in range(0, n - TD_STRIDE * 16, 4):
        ok = True
        for k in range(16):
            off = start + k * TD_STRIDE
            if off + 0x48 > n:
                ok = False
                break
            method_start = struct.unpack_from("<H", blob, off + 0x40)[0]
            method_count = struct.unpack_from("<H", blob, off + 0x42)[0]
            field_start = struct.unpack_from("<H", blob, off + 0x44)[0]
            field_count = struct.unpack_from("<H", blob, off + 0x46)[0]
            if method_count > 3000 or field_count > 3000:
                ok = False
                break
            if method_start > 400_000 or field_start > 100_000:
                ok = False
                break
        if ok:
            results.setdefault("td_candidates", []).append(start)
            if len(results["td_candidates"]) > 5:
                break
    return results


def main():
    if not META.exists():
        print(f"metadata 不存在: {META}")
        return
    blob = META.read_bytes()
    print(f"metadata {len(blob):,} B  版本 {struct.unpack_from('<I', blob, 4)[0]}")
    sanity = struct.unpack_from("<I", blob, 0)[0]
    print(f"sanity = 0x{sanity:08X} ({'OK' if sanity == 0xFAB11BAF else '不匹配'})")

    res = find_tables(blob)
    cands = res.get("td_candidates", [])
    print(f"\ntypeDefinitions 候选起点: {[hex(c) for c in cands]}")


if __name__ == "__main__":
    main()
