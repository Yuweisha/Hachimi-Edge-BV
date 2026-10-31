# Ghidra 脚本：导出指定地址范围的反编译伪代码
# @category Export
# @runtime PyGhidra

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

# 要导出的地址（运行时绝对地址 0x180000000 + RVA）
TARGETS = [
    (0x183e65b90, "CacheHorseFinishOrder"),
    (0x183e660e0, "DecidePlayerHorseIndexByFinishOrder"),
    (0x183e66c60, "GetPlayerHorseFinishOrder"),
    (0x183d0f0e0, "RaceHorseManagerBase_CalcHorseOrder"),
    (0x18258db50, "RaceSimulateData_GetResult1"),
    (0x18258daf0, "RaceSimulateData_GetResult2"),
    (0x18258d870, "RaceSimulateData_GetHorseResultData"),
    (0x183ed01c0, "rank_array_builder"),
]

prog = currentProgram
ifc = DecompInterface()
ifc.openProgram(prog)
monitor = ConsoleTaskMonitor()

fm = prog.getFunctionManager()

print("=" * 78)
print("PROGRAM: %s  base=%s" % (prog.getName(), prog.getImageBase()))
print("=" * 78)

for addr_val, label in TARGETS:
    addr = toAddr(addr_val)
    func = fm.getFunctionContaining(addr)
    if func is None:
        # 尝试在函数起点
        func = fm.getFunctionAt(addr)
    print("\n" + "=" * 78)
    print("### %s  @ 0x%X" % (label, addr_val))
    if func is None:
        print("（该地址不在任何已识别函数内）")
        continue
    print("### 函数: %s  入口 0x%X" % (func.getName(), func.getEntryPoint().getOffset()))
    res = ifc.decompileFunction(func, 60, monitor)
    if res is None or not res.decompileCompleted():
        print("（反编译失败: %s）" % (res.getErrorMessage() if res else "null"))
        continue
    print(res.getDecompiledFunction().getC())
