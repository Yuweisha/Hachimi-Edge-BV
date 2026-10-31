"""从游戏进程内存里定位并 dump 解密后的 global-metadata。

原理：metadata 头部第一个字段是 sanity = 0xFAB11BAF，
所以扫描进程所有已提交的私有内存页，找到这个 4 字节序列即为 metadata 基址。
"""
import ctypes
import struct
import sys
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100
PAGE_READABLE = (0x02, 0x04, 0x20, 0x40, 0x80)  # READONLY/READWRITE/WRITECOPY/EXECUTE_READ/EXECUTE_READWRITE


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_ulonglong),
        ("AllocationBase", ctypes.c_ulonglong),
        ("AllocationProtect", wintypes.DWORD),
        ("__alignment1", wintypes.DWORD),
        ("RegionSize", ctypes.c_ulonglong),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("__alignment2", wintypes.DWORD),
    ]


k32.OpenProcess.restype = wintypes.HANDLE
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.restype = wintypes.BOOL


def find_pids(name_part):
    """用 tasklist 找进程 id（避免额外依赖 psutil）"""
    import subprocess
    out = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, errors="ignore"
    ).stdout
    pids = []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and name_part.lower() in parts[0].lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def main():
    pids = find_pids("UmamusumePrettyDerby")
    if not pids:
        print("游戏进程未找到")
        return 1
    pid = pids[0]
    print("游戏进程 PID =", pid)

    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        print("OpenProcess 失败，错误码 =", ctypes.get_last_error(), "（可能需要管理员权限）")
        return 1

    needle = struct.pack("<I", 0xFAB11BAF)
    addr = 0
    found = []
    mbi = MEMORY_BASIC_INFORMATION64()
    scanned = 0

    while k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        base = mbi.BaseAddress
        size = mbi.RegionSize
        if size == 0:
            addr = base + 0x1000
            continue
        readable = (
            mbi.State == MEM_COMMIT
            and (mbi.Protect & PAGE_NOACCESS) == 0
            and (mbi.Protect & PAGE_GUARD) == 0
        )
        if readable and size < 0x40000000:  # 跳过超大保留区
            buf = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)):
                scanned += got.value
                off = buf.raw.find(needle)
                while off >= 0:
                    found.append((base + off, got.value))
                    if len(found) >= 8:
                        break
                    off = buf.raw.find(needle, off + 1)
        addr = base + size
        if len(found) >= 8:
            break

    print("扫描 %.1f MB，找到 %d 处 candidate" % (scanned / 1048576, len(found)))
    for va, _ in found:
        hdr = ctypes.create_string_buffer(64)
        got = ctypes.c_size_t(0)
        if k32.ReadProcessMemory(h, ctypes.c_void_p(va), hdr, 64, ctypes.byref(got)):
            sanity, version = struct.unpack_from("<Ii", hdr.raw, 0)
            print("  VA=0x%016x  version=%d" % (va, version))
            if 20 <= version <= 40:
                fields = struct.unpack_from("<" + "i" * 28, hdr.raw, 8)
                for k, nm in enumerate(["stringLiteral", "stringLiteralData", "string",
                                        "events", "properties", "methods", "parameters",
                                        "fields", "typeDefinitions"]):
                    o, s = fields[k * 2], fields[k * 2 + 1]
                    if 0 < s:
                        print("      %-18s off=0x%08x size=0x%08x" % (nm, o, s))
                # 保存基址
                with open(r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/metadata_base.txt", "w") as f:
                    f.write("0x%x\n" % va)
                print("      -> 已记录到 docs/metadata_base.txt")
    k32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
