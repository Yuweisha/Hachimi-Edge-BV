"""扫描 GameAssembly，找 LiveTheaterInfo.IsPlayable (+0xB6) 的写入指令。

set_IsPlayable 本体是 `mov byte ptr [rcx+0xb6], dl; ret`，
il2cpp 很可能把它内联到调用点，所以直接扫机器码模式：
    88 9? b6 00 00 00   mov byte ptr [reg+0xb6], dl
    88 8? b6 00 00 00   mov byte ptr [reg+0xb6], cl
    C6 8? b6 00 00 00 ??  mov byte ptr [reg+0xb6], imm8
"""
import re
import struct

PATH = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll"
data = open(PATH, "rb").read()
print("image: %.1f MB" % (len(data) / 1048576))

PATTERNS = [
    (b"\x88\x99\xb6\x00\x00\x00", "mov [rcx+0b6h], bl"),
    (b"\x88\x91\xb6\x00\x00\x00", "mov [rcx+0b6h], dl"),
    (b"\x88\x90\xb6\x00\x00\x00", "mov [rax+0b6h], dl"),
    (b"\x88\x91\xb6\x00\x00\x00", "mov [rcx+0b6h], dl"),
    (b"\x88\x92\xb6\x00\x00\x00", "mov [rdx+0b6h], dl"),
    (b"\x88\x93\xb6\x00\x00\x00", "mov [rbx+0b6h], dl"),
    (b"\x88\x96\xb6\x00\x00\x00", "mov [rsi+0b6h], dl"),
    (b"\x88\x97\xb6\x00\x00\x00", "mov [rdi+0b6h], dl"),
    (b"\x88\x95\xb6\x00\x00\x00", "mov [rbp+0b6h], dl"),
    (b"\xc6\x81\xb6\x00\x00\x00", "mov byte [rcx+0b6h], imm8"),
    (b"\xc6\x82\xb6\x00\x00\x00", "mov byte [rdx+0b6h], imm8"),
    (b"\xc6\x83\xb6\x00\x00\x00", "mov byte [rbx+0b6h], imm8"),
    (b"\xc6\x86\xb6\x00\x00\x00", "mov byte [rsi+0b6h], imm8"),
    (b"\xc6\x87\xb6\x00\x00\x00", "mov byte [rdi+0b6h], imm8"),
]

hits = []
for pat, name in PATTERNS:
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        hits.append((i, name))
        start = i + 1

hits.sort()
print("命中 %d 处" % len(hits))
for off, name in hits[:40]:
    print("  rva %#x  %s" % (off, name))

# 同时找 call set_IsPlayable (0x38f1740)
print("\n=== call 0x38f1740 ===")
tgt = 0x38F1740
cnt = 0
i = 0
while True:
    i = data.find(b"\xe8", i)
    if i < 0:
        break
    rel = struct.unpack_from("<i", data, i + 1)[0]
    if (i + 5 + rel) & 0xFFFFFFFF == tgt or i + 5 + rel == tgt:
        print("  rva %#x" % i)
        cnt += 1
    i += 1
print("共 %d 处" % cnt)
