"""扫描 GameAssembly_unpacked.dll 里所有 call/jmp 到指定目标 RVA 的位置。"""
import struct
import sys
from pathlib import Path

DLL = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll")
IMAGE_BASE = 0x180000000
SECTIONS = [
    (".text",  0x00001000, 0x490000, 0x00001000),
    ("il2cpp", 0x00491000, 0x5E1F000, 0x00491000),
]

def find_callers(target_rva: int, limit=40):
    """找所有 E8/E9 rel32 指向 target_rva 的位置。"""
    data = DLL.read_bytes()
    target = IMAGE_BASE + target_rva
    hits = []
    for name, va, vsz, ro in SECTIONS:
        start = ro
        end = ro + vsz
        chunk = data[start:end]
        # 扫 E8/E9
        i = 0
        n = len(chunk)
        while i < n - 5:
            if chunk[i] in (0xE8, 0xE9):
                rel = struct.unpack_from("<i", chunk, i + 1)[0]
                ins_rva = va + i
                # 目标 = 下条指令的 RVA + rel
                dst_rva = ins_rva + 5 + rel
                if dst_rva == target_rva:
                    hits.append((name, ins_rva, IMAGE_BASE + ins_rva))
                    if len(hits) >= limit:
                        return hits
            i += 1
    return hits


if __name__ == "__main__":
    targets = [
        (0x258db50, "GetResult #1"),
        (0x258daf0, "GetResult #2"),
        (0x258d490, "GetFirstReachedTimeByDistance"),
        (0x258dd70, "GetTopHorseIndexByFrame"),
    ]
    for rva, label in targets:
        hits = find_callers(rva)
        print(f"\n{'=' * 70}")
        print(f"{label}  (RVA 0x{rva:x})  调用者 {len(hits)} 处")
        for sec, crva, caddr in hits[:20]:
            print(f"  {sec}  RVA=0x{crva:x}   addr=0x{caddr:x}")
