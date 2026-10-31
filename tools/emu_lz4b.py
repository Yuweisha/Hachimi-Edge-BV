"""Unicorn 模拟 libnative!LZ4_decompress_safe_ext —— 修正版：IAT 填 stub。"""

import struct
from collections import Counter

from unicorn import (
    Uc,
    UcError,
    UC_ARCH_X86,
    UC_MODE_64,
    UC_HOOK_CODE,
)
from unicorn.x86_const import (
    UC_X86_REG_RSP,
    UC_X86_REG_RIP,
    UC_X86_REG_RAX,
    UC_X86_REG_RCX,
    UC_X86_REG_RDX,
    UC_X86_REG_R8,
    UC_X86_REG_R9,
)

DUMP = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/libnative_unpacked.dll"
BASE = 0x180000000
STACK = 0x190000000
STACK_SIZE = 0x100000
SCRATCH = 0x1A0000000
SCRATCH_SIZE = 0x4000000
STUB = SCRATCH + 0x3000000  # 放一个 ret 指令
DEC_RVA = 0x3180


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def u64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def align_up(v, a=0x1000):
    return (v + a - 1) & ~(a - 1)


def patch_iat(data):
    """把 IAT 里的 name-RVA 全部替换成 STUB 的相对地址占位（0 表示待填）。

    返回 (patched_data, iat_slots)。
    """
    buf = bytearray(data)
    e = u32(buf, 0x3C)
    opt = e + 0x18
    magic = u16(buf, opt)
    dd = opt + (0x70 if magic == 0x20B else 0x60)
    imp = u32(buf, dd + 8)

    slots = []
    off = imp
    while True:
        d = off
        name_rva = u32(buf, d + 12)
        ft = u32(buf, d + 16)
        oft = u32(buf, d)
        if name_rva == 0:
            break
        name = bytes(buf[name_rva:buf.index(0, name_rva)]).decode("ascii", "ignore")
        src_off = oft if oft else ft
        i = 0
        while True:
            t = u64(buf, src_off + i * 8)
            if t == 0:
                break
            fn = None
            if not (t >> 63):
                nr = (t & 0x7FFFFFFF) + 2
                fn = bytes(buf[nr:buf.index(0, nr)]).decode("ascii", "ignore")
            slots.append((name, fn, ft + i * 8))
            # 用占位：stub 的 RVA（未加 BASE）
            struct.pack_into("<Q", buf, ft + i * 8, STUB)
            i += 1
        off += 20
    # 暴力：IAT 区域里所有像用户态地址的 8 字节值统一替换成 STUB
    for o in range(imp, imp + 0x200, 8):
        v = u64(buf, o)
        if 0x10000 < v < 0x00007FFFFFFF0000:
            struct.pack_into("<Q", buf, o, STUB)
    return bytes(buf), slots


def main():
    data = open(DUMP, "rb").read()
    patched, slots = patch_iat(data)
    print("IAT 槽 %d 个:" % len(slots))
    for dll, fn, off in slots:
        print("   %-16s %s" % (dll, fn))

    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    size = align_up(len(patched))
    uc.mem_map(BASE, size)
    uc.mem_write(BASE, patched)
    uc.mem_map(STACK, STACK_SIZE)
    uc.mem_map(SCRATCH, SCRATCH_SIZE)
    uc.mem_write(STUB, b"\xC3")  # ret

    src = open("C:/FiddlerDump/lz4pairs/000_src.bin", "rb").read()
    dst = open("C:/FiddlerDump/lz4pairs/000_dst.bin", "rb").read()

    src_va = SCRATCH
    dst_va = SCRATCH + 0x100000
    uc.mem_write(src_va, src)
    uc.mem_write(dst_va, b"\x00" * (len(dst) + 512))

    sp = STACK + STACK_SIZE - 0x1000
    uc.reg_write(UC_X86_REG_RSP, sp)
    uc.reg_write(UC_X86_REG_RCX, src_va)
    uc.reg_write(UC_X86_REG_RDX, dst_va)
    uc.reg_write(UC_X86_REG_R8, len(src))
    # dstCapacity 必须精确等于 srcSize + declared（游戏里就是这个值）
    declared = struct.unpack_from("<I", src, 0)[0]
    uc.reg_write(UC_X86_REG_R9, len(src) + declared)
    # 主函数返回地址放一个哨兵
    RET_MAGIC = 0x1BF00000
    uc.mem_map(0x1BF00000, 0x1000)
    uc.mem_write(RET_MAGIC, bytes([0xF4]))
    uc.mem_write(sp, struct.pack("<Q", RET_MAGIC))

    stub_hits = Counter()
    last_rip = [0]

    def on_code(uc_, address, size_, user_data):
        last_rip[0] = address
        # 任何跳到映像外的执行都当作外部调用，立即返回
        if not (BASE <= address < BASE + size):
            ret = struct.unpack("<Q", uc_.mem_read(uc_.reg_read(UC_X86_REG_RSP), 8))[0]
            uc_.reg_write(UC_X86_REG_RSP, uc_.reg_read(UC_X86_REG_RSP) + 8)
            uc_.reg_write(UC_X86_REG_RIP, ret)
            uc_.reg_write(UC_X86_REG_RAX, 0)
            stub_hits[address] += 1
            return
        if address == STUB:
            ret = struct.unpack("<Q", uc_.mem_read(uc_.reg_read(UC_X86_REG_RSP), 8))[0]
            uc_.reg_write(UC_X86_REG_RSP, uc_.reg_read(UC_X86_REG_RSP) + 8)
            uc_.reg_write(UC_X86_REG_RIP, ret)
            uc_.reg_write(UC_X86_REG_RAX, 0)
            stub_hits[ret - BASE] += 1

    uc.hook_add(UC_HOOK_CODE, on_code)

    try:
        uc.emu_start(BASE + DEC_RVA, RET_MAGIC, count=5000000)
    except UcError as exc:
        ip = uc.reg_read(UC_X86_REG_RIP)
        print("UcError: %s  rip=%#x (rva %#x) 最后执行 rva=%#x"
              % (exc, ip, ip - BASE, last_rip[0] - BASE))
    else:
        print("正常返回")

    print("stub 调用 %d 次" % sum(stub_hits.values()))
    for rva, cnt in stub_hits.most_common(15):
        print("   返回点 rva %#x  x%d" % (rva, cnt))

    got = bytes(uc.mem_read(dst_va, len(dst)))
    print("\n输出:", got[:32].hex(" "))
    print("期望:", dst[:32].hex(" "))
    print("一致:", got == dst)


if __name__ == "__main__":
    main()
