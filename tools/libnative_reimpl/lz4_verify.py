"""Verify decryption candidates by feeding them to standard LZ4.

0x173210 in libnative is a textbook LZ4 block decoder:
    token = *src; lit_len = token >> 4;
    if lit_len == 15: accumulate 0xff run
    copy literals; then match (len = token & 0xf, offset)

So any correct decryption must produce a buffer that lz4.block accepts.
"""
import glob, os, struct
import lz4.block
from pcg_keystream import PCG32
from tree_codec import sbox_from_pcg, permute

def try_lz4(data, declared):
    for kwargs in ({'uncompressed_size': declared}, {}):
        try:
            out = lz4.block.decompress(data, **kwargs)
            return out
        except Exception:
            pass
    return None

print(f'{"sample":16s} {"variant":12s} {"lz4":6s} {"out":>10s} {"declared":>10s}  head')
for p in sorted(glob.glob(r'C:/FiddlerDump/lz4pairs/*_src.bin')):
    src = open(p, 'rb').read()
    if len(src) < 12:
        continue
    declared = struct.unpack_from('<I', src, 0)[0]
    payload = src[4:]
    if declared == 0:
        continue
    base = os.path.basename(p)

    cands = {}
    # A: 原始 payload（无解密）
    cands['raw'] = payload
    # B: 跳过前 10 字节种子
    cands['skip10'] = payload[10:]
    # C: PCG-XOR
    g = PCG32.from_bytes(payload, 0)
    cands['pcg-xor'] = bytes(a ^ b for a, b in zip(payload[10:], g.keystream(len(payload) - 10)))
    # D: S-box 置换
    g = PCG32.from_bytes(payload, 0)
    cands['sbox'] = permute(payload[10:], sbox_from_pcg(g), payload[:10])

    for name, data in cands.items():
        out = try_lz4(data, declared)
        if out is not None:
            ok = 'MATCH' if len(out) == declared else 'SIZE?'
            head = out[:16].hex() if out else '-'
            print(f'{base:16s} {name:12s} {ok:6s} {len(out):>10,} {declared:>10,}  {head}')
        else:
            pass
print('\n(只显示 lz4 成功解压的候选)')
