"""用 Unicorn 模拟执行 libnative!LZ4_decompress_safe_ext，观察它如何变换数据。

思路：把重建后的 PE 整体按 RVA 映射（该 dump 的文件偏移 == RVA），
然后像调用普通函数一样设置寄存器并运行。遇到未映射的跳转（= API 调用）
就记录下来并 stub 返回，逐步补齐即可跑通。
"""

import struct
import sys

from unicorn import (
    Uc,
    UcError,
    UC_ARCH_X86,
    UC_MODE_64,
    UC_HOOK_CODE,
    UC_HOOK_MEM_UNMAPPED,
)
from unicorn.x86_const import (
    UC_X86_REG_RCX,
    UC_X86_REG_RDX,
    UC_X86_REG_R8,
    UC_X86_REG_R9,
    UC_X86_REG_RSP,
    UC_X86_REG_RIP,
    UC_X86_REG_RAX,
)

DUMP = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/libnative_unpacked.dll"
BASE = 0x180000000
STACK = 0x190000000
STACK_SIZE = 0x100000
SCRATCH = 0x1A0000000
SCRATCH_SIZE = 0x2000000

DEC_RVA = 0x3180


def align_down(v, a=0x1000):
    return v & ~(a - 1)


def align_up(v, a=0x1000):
    return (v + a - 1) & ~(a - 1)


def load_image(uc, data):
    """按 RVA 映射整个文件（dump 已重建，偏移==RVA）。"""
    size = align_up(len(data))
    uc.mem_map(BASE, size)
    uc.mem_write(BASE, data)
    return size


def main():
    data = open(DUMP, "rb").read()
    print("image: %d bytes" % len(data))

    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    size = load_image(uc, data)
    uc.mem_map(STACK, STACK_SIZE)
    uc.mem_map(SCRATCH, SCRATCH_SIZE)
    print("mapped image @ %#x (%#x), stack @ %#x, scratch @ %#x" % (BASE, size, STACK, SCRATCH))

    src = open("C:/FiddlerDump/lz4pairs/000_src.bin", "rb").read()
    dst = open("C:/FiddlerDump/lz4pairs/000_dst.bin", "rb").read()

    src_va = SCRATCH
    dst_va = SCRATCH + 0x100000
    uc.mem_write(src_va, src)
    uc.mem_write(dst_va, b"\x00" * (len(dst) + 512))

    uc.reg_write(UC_X86_REG_RSP, STACK + STACK_SIZE - 0x1000)
    uc.reg_write(UC_X86_REG_RCX, src_va)
    uc.reg_write(UC_X86_REG_RDX, dst_va)
    uc.reg_write(UC_X86_REG_R8, len(src))
    uc.reg_write(UC_X86_REG_R9, len(dst) + 512)

    calls = []
    blocks = []

    def on_unmapped(uc_, access, address, size_, value, user_data):
        blocks.append((uc_.reg_read(UC_X86_REG_RIP), address, size_))
        return False

    def on_code(uc_, address, size_, user_data):
        # 记录跳到映像外的调用
        if not (BASE <= address < BASE + len(data)):
            blocks.append((uc_.reg_read(UC_X86_REG_RIP), address, 0))
            # 直接从返回地址继续
            ret = struct.unpack("<Q", uc.mem_read(uc_.reg_read(UC_X86_REG_RSP), 8))[0]
            uc.reg_write(UC_X86_REG_RSP, uc.reg_read(UC_X86_REG_RSP) + 8)
            uc.reg_write(UC_X86_REG_RIP, ret)
            uc.reg_write(UC_X86_REG_RAX, 0)
            return

    uc.hook_add(UC_HOOK_MEM_UNMAPPED, on_unmapped)
    uc.hook_add(UC_HOOK_CODE, on_code)

    try:
        uc.emu_start(BASE + DEC_RVA, BASE + len(data), count=2000000)
    except UcError as exc:
        ip = uc.reg_read(UC_X86_REG_RIP)
        print("UcError: %s  rip=%#x (rva %#x)" % (exc, ip, ip - BASE))
    else:
        print("正常结束")

    print("外部调用/未映射访问记录 %d 条" % len(blocks))
    for ip, addr, sz in blocks[:20]:
        print("  from rva %#x -> %#x size=%d" % (ip - BASE, addr, sz))

    got = uc.mem_read(dst_va, len(dst))
    print("\n输出前 32 字节:", bytes(got[:32]).hex(" "))
    print("期望前 32 字节:", dst[:32].hex(" "))
    print("完全一致:", bytes(got) == dst)


if __name__ == "__main__":
    main()
