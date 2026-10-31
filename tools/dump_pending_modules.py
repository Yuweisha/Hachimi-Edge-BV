"""轮询等待指定模块被加载后自动脱壳（重建 PE，节表 rawsize=vsize）。"""
import ctypes, struct, os, sys, time
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wintypes.BOOL

TARGETS = {
    "cyspringplugin.dll": r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/CySpringPlugin_unpacked.dll",
    "lib_burst_generated.dll": r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/lib_burst_generated_unpacked.dll",
}
PID = 10256
DEADLINE = time.time() + 900


class ME(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
                ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
                ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
                ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260)]


def modules(pid):
    snap = k32.CreateToolhelp32Snapshot(0x8 | 0x10, pid)
    me = ME(); me.dwSize = ctypes.sizeof(ME)
    out = {}
    if k32.Module32FirstW(snap, ctypes.byref(me)):
        while True:
            out[me.szModule.lower()] = (
                ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value,
                me.modBaseSize, me.szExePath)
            if not k32.Module32NextW(snap, ctypes.byref(me)):
                break
    k32.CloseHandle(snap)
    return out


def dump(h, base, out_path):
    hdr = b""
    buf = ctypes.create_string_buffer(0x1000)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, 0x1000, ctypes.byref(got)):
        print("  读 PE 头失败")
        return False
    hdr = buf.raw[:got.value]
    if hdr[:2] != b"MZ":
        print("  不是 PE")
        return False
    e = struct.unpack_from("<I", hdr, 0x3c)[0]
    nsec = struct.unpack_from("<H", hdr, e + 6)[0]
    optsz = struct.unpack_from("<H", hdr, e + 20)[0]
    secbase = e + 24 + optsz
    file_align = struct.unpack_from("<I", hdr, e + 24 + 36)[0] or 0x200

    def align_up(v, a):
        return (v + a - 1) // a * a

    secs = []
    for i in range(nsec):
        o = secbase + i * 40
        nm = hdr[o:o + 8].rstrip(b'\x00').decode('latin1', 'ignore')
        vs, va, rs, ra = struct.unpack_from("<IIII", hdr, o + 8)
        secs.append((nm, va, vs, rs))

    headers_size = align_up(secbase + nsec * 40, file_align)
    ptr = headers_size
    new = []
    for nm, va, vs, rs in secs:
        raw = align_up(max(vs, 1), file_align)
        new.append((nm, va, vs, raw, ptr))
        ptr += raw

    out_hdr = bytearray(hdr[:headers_size])
    for i, (nm, va, vs, raw, rp) in enumerate(new):
        o = secbase + i * 40
        struct.pack_into("<I", out_hdr, o + 16, raw)
        struct.pack_into("<I", out_hdr, o + 20, rp)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(out_hdr)
        for nm, va, vs, raw, rp in new:
            size = max(vs, 0x1000)
            chunk = ctypes.create_string_buffer(size)
            g = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base + va), chunk, size, ctypes.byref(g)):
                data = chunk.raw[:g.value]
            else:
                data = b""
            if len(data) < size:
                data += b"\x00" * (size - len(data))
            f.write(data)
            if raw > size:
                f.write(b"\x00" * (raw - size))
    print(f"  已写 {out_path} ({os.path.getsize(out_path):,} bytes), 节: {[s[0] for s in secs]}")
    return True


print("等待模块加载（最多 15 分钟）…", flush=True)
done = set()
while time.time() < DEADLINE and len(done) < len(TARGETS):
    try:
        mods = modules(PID)
    except Exception as ex:
        print("枚举失败:", ex, flush=True)
        time.sleep(3)
        continue
    for name, out in TARGETS.items():
        if name in done:
            continue
        if name in mods:
            base, size, path = mods[name]
            print(f"[+] {name} 已加载 base={base:#x} size={size:,}", flush=True)
            h = k32.OpenProcess(0x0010 | 0x0400, False, PID)
            if h:
                if dump(h, base, out):
                    done.add(name)
                k32.CloseHandle(h)
            else:
                print("  OpenProcess 失败", ctypes.get_last_error(), flush=True)
        else:
            print(f"… {name} 尚未加载", flush=True)
    time.sleep(5)

print("结束。完成:", sorted(done), flush=True)
