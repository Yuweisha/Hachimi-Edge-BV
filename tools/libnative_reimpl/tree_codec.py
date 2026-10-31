"""Tree codec skeleton for libnative's LZ4_decompress_safe_ext.

Layers confirmed from the decompiled binary:

  bignum   0x46600 cmp / 0x46830 sub / 0x46e60 add / 0x472f0 div / 0x3bbc0 mod
  cipher   PCG32 (0x5851f42d4c957f2d / ...f2e) + 16-entry S-box, three-way XOR
  tree     48-byte nodes = left(16) | right(16) | parent(16), five functions recurse x3
  layout   0x3e180: >383 bytes -> 32 blocks, else 16 blocks; each block 48 bytes

This module wires those layers into a runnable decoder and reports which stage
the sample pairs fail at. It is intentionally explicit about unknowns rather
than guessing silently.
"""

from __future__ import annotations

import struct

from pcg_keystream import PCG32

MASK64 = 0xFFFFFFFFFFFFFFFF
MASK8 = 0xFF


# ---------------------------------------------------------------- cipher

def sbox_from_pcg(pcg: PCG32, n: int = 16) -> bytearray:
    """Fill an n-entry S-box from the PCG keystream.

    The decompiled code writes PCG output bytes into consecutive slots
    (pbVar34[-2], [-1], [0], [1], ... pbVar34[6]) before each 9-byte advance,
    so the S-box is simply the first n keystream bytes.
    """
    return bytearray(pcg.keystream(n))


def permute(data: bytes, sbox: bytearray, extra: bytes) -> bytes:
    """S-box driven state machine recovered from 0x310f0.

    Per input byte b:
        i = (b ^ extra[pos]) & 0xf
        s = sbox[i]
        j = (b ^ s) & 0xf
        t = state[j]
        state[j] ^= b ^ extra[pos]
        k = (b ^ t) & 0xf
        state[k] ^= b ^ s
        out = ...
    The exact output byte blending is not yet certain; this function returns the
    intermediate state so the caller can test both plausible outputs.
    """
    state = bytearray(sbox)
    out = bytearray(len(data))
    for pos, b in enumerate(data):
        e = extra[pos % len(extra)] if extra else 0
        i = (b ^ e) & 0x0F
        s = state[i]
        j = (b ^ s) & 0x0F
        t = state[j]
        state[j] ^= b ^ e
        k = (b ^ t) & 0x0F
        state[k] ^= b ^ s
        out[pos] = t
    return bytes(out)


# ---------------------------------------------------------------- tree

NODE = 0x30
HALF = 0x10


class Node:
    __slots__ = ("left", "right", "parent")

    def __init__(self):
        self.left = 0
        self.right = 0
        self.parent = 0

    @classmethod
    def from_bytes(cls, buf: bytes, off: int):
        n = cls()
        n.left = int.from_bytes(buf[off:off + HALF], "little")
        n.right = int.from_bytes(buf[off + HALF:off + 2 * HALF], "little")
        n.parent = int.from_bytes(buf[off + 2 * HALF:off + 3 * HALF], "little")
        return n

    def to_bytes(self) -> bytes:
        return (self.left.to_bytes(HALF, "little")
                + self.right.to_bytes(HALF, "little")
                + self.parent.to_bytes(HALF, "little"))


def build_tree(blocks: list[bytes]) -> list[Node]:
    """Build the 2^k node array: leaves first, then one parent per pair.

    0x3ceb0 walks `local_78[lvar5] = uvar3 * 0x30 + param_2` with uvar3
    doubling each step, i.e. nodes at indices 1, 2, 4, 8, ... are the roots of
    each subtree level.
    """
    nodes = [Node.from_bytes(b, 0) if len(b) >= NODE else Node() for b in blocks]
    # pad to power of two
    n = 1
    while n < len(nodes):
        n <<= 1
    while len(nodes) < n:
        nodes.append(Node())

    # merge upward: parent.left = left subtree root, parent.right = right root
    level = nodes[:]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            p = Node()
            p.left = level[i].parent or level[i].left
            p.right = level[i + 1].parent or level[i + 1].right
            p.parent = (p.left + p.right) & ((1 << (HALF * 8)) - 1)
            nxt.append(p)
        level = nxt
    return nodes + level


# ---------------------------------------------------------------- top level

def decode(src: bytes, variant: int = 0) -> tuple[bytes, str]:
    """Attempt to decode one body. Returns (output, stage_reached)."""
    if len(src) < 8:
        return b"", "too-short"

    declared = struct.unpack_from("<I", src, 0)[0]
    payload = src[4:]
    if declared == 0:
        return b"", "declared-zero"

    # stage 1: PCG seeding from the payload head
    pcg = PCG32.from_bytes(payload, 0)
    if variant == 0:
        state = bytearray(pcg.keystream(len(payload) - 10))
        body = bytes(b ^ k for b, k in zip(payload[10:], state))
        stage = "pcg-xor"
    elif variant == 1:
        sbox = sbox_from_pcg(pcg)
        body = permute(payload[10:], sbox, payload[:10])
        stage = "sbox-permute"
    else:
        return b"", "bad-variant"

    # stage 2: block split (>383 bytes -> 32 blocks, else 16)
    nblocks = 32 if len(payload) > 0x17F else 16
    bs = max(1, (len(body) + nblocks - 1) // nblocks)
    blocks = [body[i:i + bs].ljust(NODE, b"\x00")[:NODE] for i in range(0, len(body), bs)]

    # stage 3: tree build
    nodes = build_tree(blocks)

    # stage 4: flatten
    out = b"".join(n.to_bytes() for n in nodes)
    return out[:declared], stage


if __name__ == "__main__":
    import glob
    import os

    print("Decoder skeleton -- reporting the stage each sample reaches\n")
    for p in sorted(glob.glob(r"C:/FiddlerDump/lz4pairs/*_src.bin")):
        src = open(p, "rb").read()
        dst_p = p.replace("_src.bin", "_dst.bin")
        dst = open(dst_p, "rb").read() if os.path.exists(dst_p) else b""
        declared = struct.unpack_from("<I", src, 0)[0]

        for v in (0, 1):
            out, stage = decode(src, v)
            match = out[:len(dst)] == dst if out else False
            head = out[:16].hex() if out else "-"
            print(f"  {os.path.basename(p):14s} v{v} {stage:14s} "
                  f"out={len(out):>8,}/{declared:<8,} match={match}  {head}")
        print()
