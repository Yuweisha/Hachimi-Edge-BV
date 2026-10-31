"""反汇编 GameAssembly_unpacked.dll 指定 RVA 区间。"""
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

def disas_range(start_rva, nbytes=512, label=""):
    off, sec = rva_to_off(start_rva)
    if off is None:
        print(f"{label} RVA 0x{start_rva:x} 不在节内")
        return
    code = data[off:off + nbytes]
    print(f"\n{'=' * 76}")
    print(f"{label}  RVA=0x{start_rva:x}..0x{start_rva + nbytes:x}  sec={sec}")
    for ins in md.disasm(code, 0x180000000 + start_rva):
        mark = ""
        op = ins.op_str
        # 标记 call 目标
        if ins.mnemonic == "call" and op.startswith("0x"):
            try:
                tgt = int(op, 16)
                mark = f"   → RVA 0x{tgt - 0x180000000:x}"
            except ValueError:
                pass
        print(f"  0x{ins.address:x}: {ins.mnemonic:<8} {op}{mark}")


if __name__ == "__main__":
    ranges = [
        (0x3df9700, 0x180, "调用点群 A (3 处连续)"),
        (0x3dfa800, 0x140, "调用点群 B"),
        (0x3dfe900, 0x140, "调用点群 C"),
    ]
    for rva, nb, lab in ranges:
        disas_range(rva, nb, lab)
