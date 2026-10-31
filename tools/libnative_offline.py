"""离线加载 libnative.dll（跳过 DllMain）并手工填充 IAT，使 LZ4_*_ext 可调用。"""
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

DLL_PATH = (
    r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
    r"/UmamusumePrettyDerby_Jpn_Data/Plugins/x86_64/libnative.dll"
)


def u16(a):
    return ctypes.c_uint16.from_address(a).value


def u32(a):
    return ctypes.c_uint32.from_address(a).value


def u64(a):
    return ctypes.c_uint64.from_address(a).value


def load_and_fix():
    """加载模块并解析导入表，返回模块基址。"""
    base = k32.LoadLibraryExW(DLL_PATH, None, 0x1)  # DONT_RESOLVE_DLL_REFERENCES
    if not base:
        raise OSError("LoadLibraryEx failed: %d" % ctypes.get_last_error())

    e_lfanew = u32(base + 0x3C)
    opt = base + e_lfanew + 0x18
    magic = u16(opt)
    dd = opt + (0x70 if magic == 0x20B else 0x60)
    imp_rva = u32(dd + 8)

    off = imp_rva
    resolved = 0
    dlls = []
    while True:
        desc = base + off
        oft = u32(desc)
        name_rva = u32(desc + 12)
        ft = u32(desc + 16)
        if name_rva == 0:
            break
        dll = ctypes.string_at(base + name_rva).decode("ascii", "ignore")
        dlls.append(dll)
        hmod = k32.LoadLibraryW(dll)
        if hmod:
            thunk_off = oft if oft else ft
            i = 0
            while True:
                t = u64(base + thunk_off + i * 8)
                if t == 0:
                    break
                if t >> 63:
                    ordv = t & 0xFFFF
                    fn = k32.GetProcAddress(hmod, ctypes.c_char_p(struct.pack("<H", ordv)))
                else:
                    name_off = (t & 0x7FFFFFFF) + 2
                    fn = k32.GetProcAddress(hmod, ctypes.string_at(base + name_off))
                if fn:
                    ctypes.c_uint64.from_address(base + ft + i * 8).value = fn
                    resolved += 1
                i += 1
        off += 20

    return base, dlls, resolved


if __name__ == "__main__":
    base, dlls, n = load_and_fix()
    print("base = %#x" % base)
    print("依赖 %d 个 DLL: %s" % (len(dlls), ", ".join(dlls)))
    print("填充 IAT 项 %d 个" % n)

    DEC = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int
    )(k32.GetProcAddress(base, b"LZ4_decompress_safe_ext"))
    CMP = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int
    )(k32.GetProcAddress(base, b"LZ4_compress_default_ext"))

    for i in range(4):
        src = open("C:/FiddlerDump/lz4pairs/%03d_src.bin" % i, "rb").read()
        dst = open("C:/FiddlerDump/lz4pairs/%03d_dst.bin" % i, "rb").read()

        out = ctypes.create_string_buffer(len(dst) + 128)
        try:
            r = DEC(src, out, len(src), len(out))
        except Exception as exc:
            print("#%d DEC 崩溃: %s" % (i, exc))
            continue
        match = (r == len(dst)) and (out.raw[:r] == dst)
        print("#%d DEC(整段含头) -> %d (期望 %d) 一致=%s" % (i, r, len(dst), match))
        if not match and r > 0:
            print("   实际:", out.raw[:20].hex(" "))
            print("   期望:", dst[:20].hex(" "))
