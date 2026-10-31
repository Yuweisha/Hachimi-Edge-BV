"""用 metadata + methodPointers 生成 dump.cs（C# 类结构 + 方法 RVA）。

复用 parse_metadata_v31.py 的表定位逻辑，不依赖 Il2CppDumper。

用法：
    python gen_dump_cs2.py            # 生成所有类型
    python gen_dump_cs2.py Race       # 只生成名字含 Race 的类型
"""
from __future__ import annotations

import ctypes
import struct
import sys
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_metadata_v31 import Metadata, TD_STRIDE

DLL_PATH = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_rebased.dll"
META = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/metadata_jp_recovered.dat"
IMAGE_BASE = 0x180000000
METHOD_PTR_RVA = 0x69A3ED8
METHOD_PTR_COUNT = 201175

OUT_DIR = Path(r"C:/Users/Schwarz/uma_metadata")

MD_STRIDE = 0x24
FD_STRIDE = 0x10

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.restype = wintypes.HMODULE
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
DONT_RESOLVE_DLL_REFERENCES = 0x00000001


def load_method_pointers():
    h = k32.LoadLibraryExW(DLL_PATH, None, DONT_RESOLVE_DLL_REFERENCES)
    if not h:
        print("加载 DLL 失败", ctypes.get_last_error())
        return []
    base = int(h)
    table_va = base + METHOD_PTR_RVA
    out = []
    for k in range(METHOD_PTR_COUNT):
        v = ctypes.c_uint64.from_address(table_va + k * 8).value
        out.append(v - base if v >= base else 0)
    return out


def method_at(m: Metadata, i: int):
    off = m.tables['methods'][0] + i * MD_STRIDE
    name_idx = struct.unpack_from('<i', m.blob, off)[0]
    decl, ret = struct.unpack_from('<2i', m.blob, off + 4)
    token = struct.unpack_from('<I', m.blob, off + 0x14)[0]
    param_count = struct.unpack_from('<H', m.blob, off + 0x22)[0]
    return {"name": m.string(name_idx), "declaring": decl, "ret": ret,
            "token": token, "param_count": param_count}


def field_at(m: Metadata, i: int):
    off = m.tables['fields'][0] + i * FD_STRIDE
    # v31 实际：+0x00 typeIndex, +0x04 nameIndex
    type_idx, name_idx = struct.unpack_from('<2i', m.blob, off)
    return {"name": m.string(name_idx), "type": type_idx}


def gen(m: Metadata, ptrs: list[int], keyword: str | None):
    n = m.type_count()
    print(f"{n:,} 个类型，{len(ptrs):,} 个方法指针")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"dump_{keyword}.cs" if keyword else "dump_all.cs"
    out = OUT_DIR / fname

    lines = []
    written = 0
    total_methods = 0

    for i in range(n):
        t = m.type_at(i)
        name = t["name"]
        ns = t["namespace"]
        full = f"{ns}.{name}" if ns else name
        if keyword and keyword.lower() not in full.lower():
            continue
        if not name:
            continue

        lines.append(f"\n// ===== type #{i}  namespace={ns} =====")
        lines.append(f"public class {name}")
        lines.append("{")

        if t["field_count"]:
            lines.append("    // Fields")
            for k in range(t["field_count"]):
                fi = t["field_start"] + k
                try:
                    fd = field_at(m, fi)
                    lines.append(f"    public Type{fd['type']} {fd['name']};  // fieldIdx={fi}")
                except Exception:
                    lines.append(f"    // <field {fi} 读取失败>")
            lines.append("")

        if t["method_count"]:
            lines.append("    // Methods")
            for k in range(t["method_count"]):
                mi = t["method_start"] + k
                try:
                    md = method_at(m, mi)
                    rva = ptrs[mi] if mi < len(ptrs) else 0
                    lines.append(f"    // RVA: 0x{rva:X}  Token: 0x{md['token']:08X}")
                    lines.append(f"    public void {md['name']}() {{ }}  // 参数 {md['param_count']} 个")
                    total_methods += 1
                except Exception:
                    lines.append(f"    // <method {mi} 读取失败>")

        lines.append("}")
        written += 1
        if written >= 8000 and keyword is None:
            lines.append(f"\n// ... 已输出 {written} 个类型，剩余省略")
            break

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n输出 {out}  ({written:,} 个类型, {total_methods:,} 个方法)")
    print(f"{out.stat().st_size:,} B")


def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else None
    m = Metadata(META)
    ptrs = load_method_pointers()
    gen(m, ptrs, kw)


if __name__ == "__main__":
    main()
