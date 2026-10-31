"""从任意 RVA 往前找函数边界并反汇编。"""
import sys
import capstone
from pathlib import Path

DLL = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll")
data = DLL.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)


def find_func_start(target: int, max_back: int = 0x1000) -> int:
    """往前找连续 int3 填充作为函数边界。"""
    start = target
    while start > target - max_back:
        if data[start-1] == 0xCC and data[start-2] == 0xCC and data[start-3] == 0xCC:
            break
        start -= 1
    return start


def dis(start: int, nb: int, marks=None, limit=120):
    marks = marks or {}
    n = 0
    for ins in md.disasm(data[start:start+nb], 0x180000000+start):
        op = ins.op_str
        mark = ""
        if ins.mnemonic in ("call", "jmp") and op.startswith("0x"):
            try:
                t = int(op, 16) - 0x180000000
                mark = f"  -> 0x{t:x}"
                if t in marks:
                    mark += f"  ★ {marks[t]}"
            except ValueError:
                pass
        print(f"  0x{ins.address:x}: {ins.mnemonic:<8} {op}{mark}")
        n += 1
        if n >= limit:
            break


if __name__ == "__main__":
    target = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x3e68375
    MARKS = {
        0x3e65b90: "CacheHorseFinishOrder",
        0x3ed01c0: "rank array builder",
        0x258daf0: "GetResult#2",
        0x3e66c60: "GetPlayerHorseFinishOrder",
        0x3e660e0: "DecidePlayerHorseIndexByFinishOrder",
    }
    start = find_func_start(target)
    print(f"调用点 0x{target:x} 所在函数起点 0x{start:x}")
    print("=" * 70)
    dis(start, 0x500, MARKS, limit=140)
