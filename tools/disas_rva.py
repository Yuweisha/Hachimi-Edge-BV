"""反汇编 GameAssembly_unpacked.dll 里指定 RVA 的代码。"""
import sys
import capstone
from pathlib import Path

DLL = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll")
SECTIONS = [
    (".text",  0x00001000, 0x490000, 0x00001000),
    ("il2cpp", 0x00491000, 0x5E1F000, 0x00491000),
    (".rdata", 0x062B0000, 0x1344000, 0x062B0000),
]

def rva_to_off(rva):
    for name, va, vsz, ro in SECTIONS:
        if va <= rva < va + vsz:
            return ro + (rva - va), name
    return None, None

data = DLL.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = False

def disas(rva, count=40, label=""):
    off, sec = rva_to_off(rva)
    if off is None:
        print(f"{label} RVA 0x{rva:x} 不在任何节")
        return
    code = data[off:off + count * 10]
    print(f"\n{'=' * 76}")
    print(f"{label}   RVA=0x{rva:x}  file_off=0x{off:x}  sec={sec}")
    n = 0
    for ins in md.disasm(code, 0x180000000 + rva):
        print(f"  0x{ins.address:x}: {ins.mnemonic:<8} {ins.op_str}")
        n += 1
        if n >= count or ins.mnemonic in ("ret", "retf"):
            break


if __name__ == "__main__":
    targets = [
        (0x258db50, 30, "GetResult #1"),
        (0x258d870, 30, "GetHorseResultData"),
        (0x258daf0, 25, "GetResult #2"),
        (0x258d490, 35, "GetFirstReachedTimeByDistance"),
        (0x258dd70, 35, "GetTopHorseIndexByFrame"),
        (0x258d170, 25, "GetDistance"),
    ]
    for rva, cnt, lab in targets:
        disas(rva, cnt, lab)
