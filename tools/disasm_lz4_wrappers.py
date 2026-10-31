import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ga = open(r'C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll','rb').read()
pe = struct.unpack_from('<I', ga, 0x3C)[0]
nsec = struct.unpack_from('<H', ga, pe+6)[0]
optsz = struct.unpack_from('<H', ga, pe+20)[0]
so = pe + 24 + optsz
secs = []
for i in range(nsec):
    o = so + i*40
    nm = ga[o:o+8].rstrip(b'\x00').decode(errors='replace')
    vs, va, rs, rp = struct.unpack_from('<IIII', ga, o+8)
    secs.append((nm, va, vs, rp, rs))

def rva2fo(r):
    for nm, va, vs, rp, rs in secs:
        if va <= r < va + max(vs, rs):
            return rp + (r - va)
    return None

IB = 0x7FF9F2A10000
ARR = 0x069A3ED0
md = Cs(CS_ARCH_X86, CS_MODE_64)
INT3 = b'\xcc\xcc'

targets = [
    (347011, 'StreamedDecompressLZ4Bytes', 3),
    (347012, 'DecompressLZ4Bytes', 3),
    (347016, 'LZ4_decompress_safe_ext', 4),
    (347018, 'LZ4_compress_default_ext', 4),
    (347019, 'LZ4_init', 0),
]
for midx, name, argc in targets:
    ptr = struct.unpack_from('<Q', ga, ARR + midx*8)[0]
    rva = ptr - IB if ptr > IB else 0
    fo = rva2fo(rva) if rva else None
    print('')
    print('=== midx=%d %s argc=%d  ptr=0x%x rva=0x%x ===' % (midx, name, argc, ptr, rva))
    if fo is None:
        print('  未映射')
        continue
    prev = ga[fo-4:fo]
    tag = 'INT3' if prev.startswith(INT3) else ''
    print('  prev=%s %s' % (prev.hex(), tag))
    for i in list(md.disasm(ga[fo:fo+64], rva))[:12]:
        print('    0x%x  %-8s %s' % (i.address, i.mnemonic, i.op_str))
