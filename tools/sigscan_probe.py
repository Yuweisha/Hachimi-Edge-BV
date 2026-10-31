"""分析 libnative 三个关键函数的开头特征，评估 sigscan 可行性。"""
import struct

P = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/libnative_unpacked.dll"
TARGETS = {
    "0x3180 (解密入口)": 0x3180,
    "0x143210 (LZ4)": 0x143210,
    "0x14f60 (密钥流)": 0x14f60,
}

d = open(P, "rb").read()
e_lfanew = struct.unpack_from("<I", d, 0x3C)[0]
pe = e_lfanew
nsec = struct.unpack_from("<H", d, pe + 6)[0]
opt = pe + 24
magic = struct.unpack_from("<H", d, opt)[0]
sec_off = opt + struct.unpack_from("<H", d, pe + 20)[0]

secs = []
for i in range(nsec):
    o = sec_off + i * 40
    name = d[o:o+8].rstrip(b"\0").decode("ascii", "replace")
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", d, o + 8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))

for name, va, vs, rp, rs in secs:
    print(f"  {name:10s} VA={va:#010x} vsize={vs:#010x} raw={rp:#010x} rawsize={rs:#010x}")

text = next((s for s in secs if s[0] == ".text"), None)
print(f"\n.text: VA={text[1]:#x}, size={text[2]:#x}")


def rva2off(rva):
    for name, va, vs, rp, rs in secs:
        if va <= rva < va + rs:
            return rp + (rva - va)
    return None


def wildcard(bs, n=16):
    """把看起来像地址/位移的字节标成 ??（粗粒度：4 字节里出现 00 或高位）"""
    out = []
    for i, b in enumerate(bs):
        out.append(f"{b:02x}")
    return " ".join(out)


print("\n=== 各函数开头 48 字节 ===")
feats = {}
for label, rva in TARGETS.items():
    off = rva2off(rva)
    if off is None:
        print(f"{label}: RVA 不在任何节区")
        continue
    head = d[off:off + 48]
    feats[label] = head
    print(f"\n{label} @ RVA {rva:#x} (file off {off:#x})")
    print("  " + wildcard(head))
    # 检查是否以 cc 填充结尾（说明是函数边界）
    before = d[off-4:off]
    is_cc = before[:3] == b"\xcc\xcc\xcc"
    tag = "(cc 填充 OK)" if is_cc else ""
    print(f"  前 4 字节: {before.hex(' ')} {tag}")

print("\n=== 唯一性检查（16 字节前缀在 .text 中出现次数）===")
tstart, tsize = text[3], text[4]
tbody = d[tstart:tstart + tsize]
for label, head in feats.items():
    for k in (16, 24, 32):
        pat = head[:k]
        cnt = tbody.count(pat)
        print(f"  {label:24s} 前 {k:2d} 字节: {cnt} 次")
    print()
