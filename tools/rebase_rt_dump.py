"""把运行时 dump 的 GameAssembly 里所有指针从运行时绝对地址改回 ImageBase 相对。

dump 出来的 .data/.rdata 里存的是 0x7FFFxxxxxxxx 形式的运行时地址，
Il2CppDumper 等工具期待 0x180000000 + RVA。这个脚本做这个转换。

用法:
    python rebase_rt_dump.py <输入.dll> <输出.dll> [运行时基址]

运行时基址不传则自动从 .data 段推断（取落在 0x7FFF00000000~0x800000000000
范围内最小值，向下对齐到 1 MB）。
"""
import struct
import sys
from pathlib import Path

IMGBASE = 0x180000000


def parse_sections(raw):
    e_lfanew = struct.unpack_from("<I", raw, 0x3C)[0]
    opt = e_lfanew + 0x18
    nsec = struct.unpack_from("<H", raw, e_lfanew + 6)[0]
    opt_size = struct.unpack_from("<H", raw, e_lfanew + 0x14)[0]
    sec_off = opt + opt_size
    out = []
    for i in range(nsec):
        o = sec_off + i * 40
        nm = raw[o:o + 8].rstrip(b"\x00").decode("ascii", "replace")
        vsize, va, rsize, rptr = struct.unpack_from("<4I", raw, o + 8)
        out.append({"name": nm, "va": va, "vsize": vsize})
    return out, opt, e_lfanew


def detect_base(raw, secs):
    """从 .data 段推断运行时基址"""
    cands = []
    for s in secs:
        if s["name"] not in (".data", ".rdata"):
            continue
        va, vsize = s["va"], s["vsize"]
        end = min(va + vsize, len(raw))
        for k in range(va, end - 8, 8):
            v = struct.unpack_from("<Q", raw, k)[0]
            if 0x7FF000000000 <= v < 0x800000000000:
                cands.append(v)
                if len(cands) >= 5000:
                    break
        if cands:
            break
    if not cands:
        return None
    lo = min(cands)
    # 向下对齐 1 MB
    return lo & ~0xFFFFF


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    raw = bytearray(src.read_bytes())
    secs, opt, e_lfanew = parse_sections(raw)

    if len(sys.argv) > 3:
        rtbase = int(sys.argv[3], 0)
    else:
        rtbase = detect_base(raw, secs)
        if not rtbase:
            print("[x] 无法推断运行时基址")
            return 1

    limit = 0x0C000000  # 模块最大虚拟大小
    print(f"[+] 运行时基址 = 0x{rtbase:X}")
    print(f"[+] 转换范围: 0x{rtbase:X} ~ 0x{rtbase + limit:X}")

    fixed = 0
    for s in secs:
        if s["name"] == ".reloc":
            continue
        va, vsize = s["va"], s["vsize"]
        end = min(va + vsize, len(raw))
        k = va
        while k <= end - 8:
            v = struct.unpack_from("<Q", raw, k)[0]
            if rtbase <= v < rtbase + limit:
                newv = IMGBASE + (v - rtbase)
                struct.pack_into("<Q", raw, k, newv)
                fixed += 1
                k += 8
            else:
                k += 8
        print(f"    {s['name']:<10} 扫描 0x{va:08X}~0x{end:08X}")

    print(f"\n[+] 共转换 {fixed:,} 个指针")

    # 清 .reloc 段
    for s in secs:
        if s["name"] == ".reloc":
            va, vsize = s["va"], s["vsize"]
            raw[va:va + vsize] = b"\x00" * vsize
            print(f"[+] .reloc 段已清空 ({vsize:,} B)")

    # 清 BaseReloc 目录 + DYNAMIC_BASE
    dd_off = opt + 0x70
    struct.pack_into("<II", raw, dd_off + 5 * 8, 0, 0)
    dllchar = opt + 0x46
    flags = struct.unpack_from("<H", raw, dllchar)[0]
    struct.pack_into("<H", raw, dllchar, flags & ~0x40)
    print(f"[+] BaseReloc 目录清零, DllCharacteristics 0x{flags:X} → 0x{flags & ~0x40:X}")

    dst.write_bytes(raw)
    print(f"\n[+] 写出 {dst}  ({len(raw):,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
