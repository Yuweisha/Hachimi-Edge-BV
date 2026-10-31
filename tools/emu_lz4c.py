"""Unicorn 模拟 LZ4_decompress_safe_ext —— 扫描 FF15 调用槽并统一指向 stub。"""

import struct
from collections import Counter

from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_FETCH_UNMAPPED
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
STUB = SCRATCH + 0x3000000
RET_MAGIC = 0x1BF00000
DEC_RVA = 0x3180


def align_up(v, a=0x1000):
    return (v + a - 1) & ~(a - 1)


def patch_call_slots(buf):
    """扫描 FF 15 xx xx xx xx，把目标槽里的真实地址改成 STUB。"""
    n = 0
    slots = set()
    i = 0
    while i < len(buf) - 6:
        if buf[i] == 0xFF and buf[i + 1] == 0x15:
            disp = struct.unpack_from("<i", buf, i + 2)[0]
            tgt = (i + 6 + disp) & 0xFFFFFFFF
            if 0 < tgt < len(buf) - 8:
                slots.add(tgt)
            i += 6
        else:
            i += 1
    for s in slots:
        struct.pack_into("<Q", buf, s, STUB)
        n += 1
    return n, len(slots)


def main():
    data = bytearray(open(DUMP, "rb").read())
    n, ns = patch_call_slots(data)
    print("扫描到 %d 个 call[rip] 槽，改写 %d 个" % (ns, n))

    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    size = align_up(len(data))
    uc.mem_map(BASE, size)
    uc.mem_write(BASE, bytes(data))
    uc.mem_map(STACK, STACK_SIZE)
    uc.mem_map(SCRATCH, SCRATCH_SIZE)
    uc.mem_map(0x1C0000000, 0x10000000)
    uc.mem_map(0x1BF00000, 0x1000)
    uc.mem_write(STUB, bytes([0xC3]))
    uc.mem_write(RET_MAGIC, bytes([0xF4]))

    src = open("C:/FiddlerDump/lz4pairs/000_src.bin", "rb").read()
    dst = open("C:/FiddlerDump/lz4pairs/000_dst.bin", "rb").read()
    src_va = SCRATCH
    dst_va = SCRATCH + 0x100000
    uc.mem_write(src_va, src)
    uc.mem_write(dst_va, b"\x00" * (len(src) + 0x10000))

    sp = STACK + STACK_SIZE - 0x1000
    uc.reg_write(UC_X86_REG_RSP, sp)
    uc.reg_write(UC_X86_REG_RCX, src_va)
    uc.reg_write(UC_X86_REG_RDX, dst_va)
    uc.reg_write(UC_X86_REG_R8, len(src))
    declared = struct.unpack_from("<I", src, 0)[0]
    uc.reg_write(UC_X86_REG_R9, len(src) + declared)
    uc.mem_write(sp, struct.pack("<Q", RET_MAGIC))

    hits = Counter()
    heap = [0x1C0000000]
    last = [0]

    def on_code(uc_, address, size_, user_data):
        last[0] = address
        if address == STUB or not (BASE <= address < BASE + size):
            ret = struct.unpack("<Q", uc_.mem_read(uc_.reg_read(UC_X86_REG_RSP), 8))[0]
            uc_.reg_write(UC_X86_REG_RSP, uc_.reg_read(UC_X86_REG_RSP) + 8)
            uc_.reg_write(UC_X86_REG_RIP, ret)
            uc_.reg_write(UC_X86_REG_RAX, heap[0])
            heap[0] += 0x10000
            hits[address] += 1

    def on_fetch(uc_, access, address, size_, value, user_data):
        # 取指失败：当作外部调用，直接返回 0
        ret = struct.unpack("<Q", uc_.mem_read(uc_.reg_read(UC_X86_REG_RSP), 8))[0]
        uc_.reg_write(UC_X86_REG_RSP, uc_.reg_read(UC_X86_REG_RSP) + 8)
        uc_.reg_write(UC_X86_REG_RIP, ret)
        uc_.reg_write(UC_X86_REG_RAX, 0)
        hits[address] += 1
        return True

    uc.hook_add(UC_HOOK_MEM_FETCH_UNMAPPED, on_fetch)
    uc.hook_add(UC_HOOK_CODE, on_code)

    try:
        uc.emu_start(BASE + DEC_RVA, RET_MAGIC, count=20000000)
    except UcError as exc:
        ip = uc.reg_read(UC_X86_REG_RIP)
        print("UcError: %s rip=%#x rva=%#x 最后=%#x" % (exc, ip, ip - BASE, last[0] - BASE))
    else:
        print("正常返回")

    print("stub 命中 %d 次，不同目标 %d 个" % (sum(hits.values()), len(hits)))
    got = bytes(uc.mem_read(dst_va, len(dst)))
    print("输出:", got[:32].hex(" "))
    print("期望:", dst[:32].hex(" "))
    print("一致:", got == dst)


if __name__ == "__main__":
    main()
