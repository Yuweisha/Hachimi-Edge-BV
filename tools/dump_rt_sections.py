"""从运行中的游戏进程 dump GameAssembly.dll 的数据段。

Crackproof 把 GameAssembly.dll 的所有数据段（.data/.rdata/il2cpp/.pdata/.fptable）
在磁盘文件里全部清零，运行时才解密填充。所以静态分析永远拿不到 CodeRegistration。

这个脚本用 ReadProcessMemory 把运行时的段读出来，拼成一份可用的 PE，
交给 Il2CppDumper / Cpp2IL 就能正常工作。
"""
import ctypes
import os
import struct
import sys
from ctypes import wintypes

PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * 260),
    ]


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", wintypes.DWORD),
        ("EntryPoint", ctypes.c_void_p),
    ]


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
k32.Module32FirstW.restype = wintypes.BOOL
k32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.Module32NextW.restype = wintypes.BOOL
k32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
k32.CloseHandle.argtypes = [wintypes.HANDLE]


def find_pid(name):
    """按进程名找 pid"""
    import subprocess
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-Process {name} -ErrorAction SilentlyContinue).Id"],
        capture_output=True, text=True, errors="replace")
    out = r.stdout.strip()
    return int(out.split()[0]) if out else None


def find_module(pid, mod_name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap in (0, -1, 0xFFFFFFFFFFFFFFFF):
        return None
    try:
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(MODULEENTRY32W)
        ok = k32.Module32FirstW(snap, ctypes.byref(me))
        while ok:
            if me.szModule.lower() == mod_name.lower():
                return int(me.modBaseAddr), me.modBaseSize, me.szExePath
            ok = k32.Module32NextW(snap, ctypes.byref(me))
    finally:
        k32.CloseHandle(snap)
    return None


def read_mem(hp, addr, size):
    """分块读，跳过不可读的页，返回实际读到的字节。"""
    CHUNK = 0x10000
    out = bytearray()
    off = 0
    while off < size:
        n = min(CHUNK, size - off)
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t(0)
        ok = k32.ReadProcessMemory(hp, ctypes.c_void_p(addr + off), buf, n,
                                   ctypes.byref(got))
        if ok and got.value > 0:
            out += buf.raw[:got.value]
        else:
            out += b"\x00" * n
        off += n
    return bytes(out)


def parse_pe_sections(raw):
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
        out.append({"name": nm, "va": va, "vsize": vsize,
                    "rsize": rsize, "rptr": rptr})
    return out


def main():
    proc_name = sys.argv[1] if len(sys.argv) > 1 else "UmamusumePrettyderby_Jpn"
    mod_name = sys.argv[2] if len(sys.argv) > 2 else "GameAssembly.dll"
    out_path = sys.argv[3] if len(sys.argv) > 3 else r"C:/Users/Schwarz/uma_metadata/GameAssembly_rt.dll"

    pid = find_pid(proc_name)
    if not pid:
        print(f"[x] 找不到进程 {proc_name}")
        return 1
    print(f"[+] pid = {pid}")

    mi = find_module(pid, mod_name)
    if not mi:
        print(f"[x] 进程里没有 {mod_name}")
        return 1
    base, size, path = mi
    print(f"[+] {mod_name} 基址 = 0x{base:X}  大小 = 0x{size:X}")
    print(f"[+] 磁盘路径 = {path}")

    hp = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hp:
        print(f"[x] OpenProcess 失败: {ctypes.get_last_error()}")
        return 1

    try:
        # 先读 PE 头（前 0x1000 字节）拿节表
        hdr = read_mem(hp, base, 0x1000)
        if not hdr:
            print("[x] 读 PE 头失败")
            return 1
        secs = parse_pe_sections(hdr)
        print(f"\n[+] 段表（内存）:")
        for s in secs:
            print(f"    {s['name']:<10} VA=0x{s['va']:08X} VSize=0x{s['vsize']:08X}")

        # 构造输出 buffer：按 SizeOfImage 分配
        img = bytearray(size)
        # 先拷 PE 头
        img[:len(hdr)] = hdr

        # 逐段读
        # 注意：Crackproof 把 SizeOfRawData 篡改成 0x1000 来防 dump，
        # 必须一律按 VirtualSize 读，忽略 RawSize。
        print(f"\n[+] 逐段读取（按 VSize，忽略被篡改的 RawSize）...")
        for s in secs:
            addr = base + s["va"]
            n = s["vsize"]
            n = min(n, size - s["va"])
            if n <= 0:
                continue
            data = read_mem(hp, addr, n)
            if not data:
                print(f"    {s['name']:<10} 读失败")
                continue
            nz = sum(1 for b in data[:min(len(data), 100000)] if b != 0)
            img[s["va"]:s["va"] + len(data)] = data
            pct = nz / max(min(len(data), 100000), 1) * 100
            print(f"    {s['name']:<10} 读到 {len(data):>10,} B  非零 {pct:>5.1f}%")

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(img)
        print(f"\n[+] 写出 {out_path}  ({len(img):,} B)")

        # 顺手统计 .data 段的非零比例
        for s in secs:
            if s["name"] == ".data":
                seg = bytes(img[s["va"]:s["va"] + s["vsize"]])
                nz = sum(1 for b in seg[:min(len(seg), 2000000)] if b != 0)
                t = min(len(seg), 2000000)
                print(f"[+] .data 非零比例: {nz}/{t} = {nz / max(t, 1) * 100:.1f}%")
        return 0
    finally:
        k32.CloseHandle(hp)


if __name__ == "__main__":
    sys.exit(main())
