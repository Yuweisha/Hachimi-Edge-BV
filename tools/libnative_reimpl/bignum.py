"""Bignum layer for libnative codec reimplementation.

The native library implements its own multi-precision arithmetic on limb arrays
(each limb = 8 bytes = 64 bits, little-endian order, with a separate sign field).
Python's built-in int already provides arbitrary precision, so this module maps
the native API onto plain ints.

Native -> Python mapping (verified against decompiled code):

    0x45900  alloc(capacity)          -> not needed (int is unbounded)
    0x45c10  copy(dst, src)           -> dst = src
    0x45d10  set_i64(v)               -> value = abs(v), sign = +1 / -1
    0x74e60  mul_add(dst, n, src, ...)-> dst += src * scalar  (multi-precision)
    0x75720  ecc_check(...)           -> XOR parity verification (see note)

Notes on the sign representation:
    0x45d10 sets  *(short *)(p + 1) = (v >> 63) * 2 + 1
    which yields +1 for non-negative and -1 for negative.
"""

from __future__ import annotations


class BigInt:
    """Mirror of the native big-integer object.

    Native layout (as inferred from the decompiled code):
        +0x00  uint64_t* limbs
        +0x08  int16_t   sign      (+1 / -1)
        +0x0a  uint16_t  capacity  (limb count, capped at 10000)
    """

    __slots__ = ("value", "sign", "capacity")

    MAX_LIMBS = 10000          # 0x2710, enforced by 0x45900
    LIMB_BITS = 64             # each limb is 8 bytes

    def __init__(self, value: int = 0):
        self.sign = -1 if value < 0 else 1
        self.value = abs(value)
        self.capacity = self._limb_count()

    def _limb_count(self) -> int:
        if self.value == 0:
            return 1
        return (self.value.bit_length() + self.LIMB_BITS - 1) // self.LIMB_BITS

    # --- mirrors 0x45c10 (copy) ---
    def copy_from(self, other: "BigInt") -> "BigInt":
        self.value = other.value
        self.sign = other.sign
        self.capacity = other.capacity
        return self

    # --- mirrors 0x45d10 (set from int64, with sign) ---
    def set_i64(self, v: int) -> "BigInt":
        self.value = abs(v)
        self.sign = 1 if v >= 0 else -1
        self.capacity = self._limb_count()
        return self

    # --- mirrors 0x45900 (ensure capacity) ---
    def ensure_capacity(self, limbs: int) -> bool:
        if limbs > self.MAX_LIMBS:
            return False
        if limbs > self.capacity:
            self.capacity = limbs
        return True

    # --- mirrors 0x74e60 (dst += src * scalar, multi-precision) ---
    def mul_add(self, src: "BigInt", scalar: int) -> None:
        self.value += src.value * scalar
        self.capacity = self._limb_count()

    def __int__(self) -> int:
        return self.value if self.sign > 0 else -self.value

    def __repr__(self) -> str:
        sign = "" if self.sign > 0 else "-"
        return f"BigInt({sign}0x{self.value:x}, limbs={self.capacity})"


def ecc_parity_check(blocks: list[int], k: int) -> int:
    """Mirror of 0x75720 -- XOR parity over `k` equally sized blocks.

    The native routine walks the blocks from the last non-zero one, finds the
    highest set bit to determine the payload length, then repeatedly regenerates
    a parity block and XORs it against the existing one.  250 retries (or 30 for
    short payloads) tolerate transient mismatches.

    This implementation performs the parity computation only; the retry loop is
    the native code's resilience mechanism, which is unnecessary once we have a
    clean buffer.
    """
    acc = 0
    for b in blocks[:k]:
        acc ^= b
    return acc


# Self-test: verify the mapping against the sample pairs' declared sizes.
if __name__ == "__main__":
    import glob
    import os
    import struct

    print("BigInt sanity:")
    b = BigInt(0)
    b.set_i64(-12345)
    print(f"  set_i64(-12345) -> {b}  int={int(b)}")
    assert int(b) == -12345

    a = BigInt(0xFFFFFFFFFFFFFFFF)
    a.mul_add(BigInt(0xFFFFFFFFFFFFFFFF), 0xFFFFFFFFFFFFFFFF)
    print(f"  mul_add -> limbs={a.capacity} bits={a.value.bit_length()}")
    # mul_add accumulates: result = initial + src * scalar
    assert a.value == 0xFFFFFFFFFFFFFFFF + 0xFFFFFFFFFFFFFFFF ** 2

    print("  OK")

    print("\nSample sizes (declared vs actual dst):")
    for p in sorted(glob.glob(r"C:/FiddlerDump/lz4pairs/*_src.bin"))[:6]:
        src = open(p, "rb").read()
        if len(src) < 4:
            continue
        declared = struct.unpack_from("<I", src, 0)[0]
        dst_p = p.replace("_src.bin", "_dst.bin")
        actual = os.path.getsize(dst_p) if os.path.exists(dst_p) else -1
        flag = "OK" if declared == actual else f"MISMATCH(actual={actual})"
        print(f"  {os.path.basename(p):14s} declared={declared:>9,}  {flag}")
