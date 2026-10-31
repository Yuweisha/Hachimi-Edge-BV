import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

d = open(r'C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll','rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, pe+6)[0]
optsz = struct.unpack_from('<H', d, pe+20)[0]
so = pe + 24 + optsz
secs = []
for i in range(nsec):
    o = so + i*40
    nm = d[o:o+8].rstrip(b'\x00').decode(errors='replace')
    vs, va, rs, rp = struct.unpack_from('<IIII', d, o+8)
    secs.append((nm, va, vs, rp, rs))

TARGET = 0x7fcbb28
IB = 0x180000000
MASK = 0xFFFFFFFFFFFFFFFF

hits = []
for nm, va, vs, rp, rs in secs:
    if nm not in ('.text', 'il2cpp'):
        continue
    blob = d[rp:rp+rs]
    for i in range(len(blob) - 7):
        b0, b1, b2 = blob[i], blob[i+1], blob[i+2]
        is_lea = b0 in (0x48, 0x4c) and b1 == 0x8d and (b2 & 0xc7) == 0x05
        is_mov = b0 in (0x48, 0x4c) and b1 == 0x8b and (b2 & 0xc7) == 0x05
        if not (is_lea or is_mov):
            continue
        disp = struct.unpack_from('<i', blob, i+3)[0]
        addr = va + i
        tgt = (addr + 7 + disp) & MASK
        if tgt == TARGET:
            hits.append((addr, is_lea))

print('引用 0x%x 的指令 %d 处' % (TARGET, len(hits)))
md = Cs(CS_ARCH_X86, CS_MODE_64)
for a, is_lea in hits[:20]:
    fo = None
    for nm2, va2, vs2, rp2, rs2 in secs:
        if va2 <= a < va2 + rs2:
            fo = rp2 + (a - va2)
            break
    if fo is None:
        continue
    print('')
    print('=== 0x%x (RVA 0x%x) %s ===' % (a, a-IB, 'LEA' if is_lea else 'MOV'))
    for ins in list(md.disasm(d[fo:fo+48], a))[:8]:
        print('  0x%x  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
