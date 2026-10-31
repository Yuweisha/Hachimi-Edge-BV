"""离线加载 libnative.dll：跳过 DllMain、手工填充 IAT（带 VirtualProtect）。"""

import ctypes
import struct
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.LoadLibraryExW.restype = ctypes.c_void_p
k32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD]
k32.GetProcAddress.restype = ctypes.c_void_p
k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
k32.LoadLibraryW.restype = ctypes.c_void_p
k32.LoadLibraryW.argtypes = [wintypes.LPCWSTR]
k32.VirtualProtect.restype = wintypes.BOOL
k32.VirtualProtect.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]

PAGE_EXECUTE_READWRITE = 0x40
DLL_PATH = (
    r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
    r"/UmamusumePrettyDerby_Jpn_Data/Plugins/x86_64/libnative.dll"
)


def log(*a):
    print(*a, flush=True)


def u16(a):
    return ctypes.c_uint16.from_address(a).value


def u32(a):
    return ctypes.c_uint32.from_address(a).value


def u64(a):
    return ctypes.c_uint64.from_address(a).value


def load_and_fix():
    base = k32.LoadLibraryExW(DLL_PATH, None, 0x1)
    if not base:
        raise OSError("LoadLibraryEx failed: %d" % ctypes.get_last_error())
    log("base = %#x" % base)

    e = u32(base + 0x3C)
    opt = base + e + 0x18
    magic = u16(opt)
    dd = opt + (0x70 if magic == 0x20B else 0x60)
    imp_rva = u32(dd + 8)

    old = wintypes.DWORD()
    size_of_image = u32(opt + 0x38)
    ok = k32.VirtualProtect(
        ctypes.c_void_p(base), size_of_image, PAGE_EXECUTE_READWRITE, ctypes.byref(old)
    )
    log("VirtualProtect(%#x bytes) -> %s" % (size_of_image, bool(ok)))

    off = imp_rva
    resolved = 0
    dlls = []
    while True:
        d = base + off
        name_rva = u32(d + 12)
        ft = u32(d + 16)
        oft = u32(d)
        if name_rva == 0:
            break
        name = ctypes.string_at(base + name_rva).decode("ascii", "ignore")
        dlls.append(name)
        hmod = k32.LoadLibraryW(name)
        log("  %-20s hmod=%s" % (name, hex(hmod) if hmod else "NULL"))
        if hmod:
            src_off = oft if oft else ft
            i = 0
            while True:
                t = u64(base + src_off + i * 8)
                if t == 0:
                    break
                fn = None
                if t >> 63:
                    fn = k32.GetProcAddress(
                        hmod, ctypes.c_char_p(struct.pack("<H", t & 0xFFFF))
                    )
                else:
                    fn = k32.GetProcAddress(
                        hmod, ctypes.string_at(base + (t & 0x7FFFFFFF) + 2)
                    )
                if fn:
                    ctypes.c_uint64.from_address(base + ft + i * 8).value = fn
                    resolved += 1
                i += 1
        off += 20

    log("填充 IAT %d 项，依赖: %s" % (resolved, ", ".join(dlls)))
    return base


if __name__ == "__main__":
    base = load_and_fix()
    dec_addr = k32.GetProcAddress(base, b"LZ4_decompress_safe_ext")
    log("DEC @ %#x" % dec_addr)
    DEC = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int
    )(dec_addr)

    for i in range(4):
        src = open("C:/FiddlerDump/lz4pairs/%03d_src.bin" % i, "rb").read()
        dst = open("C:/FiddlerDump/lz4pairs/%03d_dst.bin" % i, "rb").read()
        out = ctypes.create_string_buffer(len(dst) + 256)
        try:
            r = DEC(src, out, len(src), len(out))
        except Exception as exc:
            log("#%d 崩溃: %s" % (i, exc))
            continue
        match = (r == len(dst)) and (out.raw[:r] == dst)
        log("#%d DEC -> %d (期望 %d) 一致=%s" % (i, r, len(dst), match))
        if not match and r > 0:
            log("   实际:", out.raw[:20].hex(" "))
            log("   期望:", dst[:20].hex(" "))
        if r < 0:
            break
