"""赛马娘 API body 解码器 —— 骨架实现

已完成：
  - body 结构解析（长度头 + 32 字节状态区）
  - PCG 密钥流（供可选的校验路径使用）
  - 比特读取器
  - 算术解码器框架（区间上下界用 Python 原生 int，替代 libnative 的大数库）

待完成：
  - 频率模型（累计频率表来源尚未确定）
  - 符号到字节的映射
  - 重归一化细节

参考：
  libnative!LZ4_decompress_safe_ext @ 0x3180
    0x3ed20  解码调度
      0x46600  大数比较   -> Python: a < b
      0x46830  大数减法   -> Python: a - b
      0x45c10  大数赋值   -> Python: a = b
      0x457a0  按 bit 选区间端点
      0x3e970  解一个符号
  libnative!FUN_7ffa1b031070 @ 0x1070  PCG 生成器
"""

import struct

MASK64 = 0xFFFFFFFFFFFFFFFF
PCG_MULT = 0x5851F42D4C957F2D

HEADER_LEN = 0x24          # 4 + 32，与 `if (param_3 < 0x24) return -1` 对应
SEED_OFF = 4
SEED_LEN = 16


# ----------------------------------------------------------------------
# PCG（仅在启用校验路径时使用；游戏实际不启用）
# ----------------------------------------------------------------------
def pcg_init(seed16: bytes):
    a = int.from_bytes(seed16[0:8], "big")
    b = int.from_bytes(seed16[8:16], "big")
    inc = (b * 2 + 1) & MASK64
    state = (((a + inc) & MASK64) * PCG_MULT + inc) & MASK64
    return state, inc


def pcg_byte(state, inc):
    """返回 (输出字节, 新状态)。对应 0x1070 的循环体。"""
    old = state
    new_state = (old * PCG_MULT + inc) & MASK64
    x = ((old >> 45) ^ (old >> 27)) & 0xFFFFFFFF
    rot = (old >> 56) >> 3          # == old >> 59
    lo8 = x & 0xFF
    out = ((lo8 << ((-rot) & 0x1F)) | (x >> rot)) & 0xFF
    return out, new_state


def pcg_keystream(state, inc, n):
    out = bytearray(n)
    for i in range(n):
        out[i], state = pcg_byte(state, inc)
    return bytes(out)


# ----------------------------------------------------------------------
# 比特读取器
# ----------------------------------------------------------------------
class BitReader:
    """位流读取。libnative 里是 `0x457a0`/`0x46600` 配合大数区间运作。"""

    def __init__(self, data: bytes, bit_offset: int = 0):
        self.data = data
        self.pos = bit_offset

    def get_bit(self) -> int:
        if self.pos >= len(self.data) * 8:
            raise EOFError("bit stream exhausted")
        byte = self.data[self.pos >> 3]
        bit = (byte >> (7 - (self.pos & 7))) & 1
        self.pos += 1
        return bit

    def get_bits(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v = (v << 1) | self.get_bit()
        return v

    def remaining_bits(self) -> int:
        return len(self.data) * 8 - self.pos


# ----------------------------------------------------------------------
# 算术解码器框架
# ----------------------------------------------------------------------
class RangeDecoder:
    """区间解码器。

    libnative 用任意精度整数维护 [low, high)：
        0x46600  比较两个区间端点
        0x46830  相减
        0x45c10  赋值
        0x457a0  按 bit 在两端之间选择

    Python 的 int 无界，直接等价于那套大数库。
    """

    def __init__(self, reader: BitReader, precision: int = 32):
        self.reader = reader
        self.precision = precision
        self.low = 0
        self.high = (1 << precision) - 1
        self.code = 0
        # 预读 precision 位作为初始码值
        for _ in range(precision):
            self.code = (self.code << 1) | reader.get_bit()

    # ---- 基础区间操作，对应 libnative 的三个大数函数 ----
    def range_size(self) -> int:
        return self.high - self.low + 1

    def split(self, cum_low: int, cum_high: int, total: int):
        """按累计频率 [cum_low, cum_high) 收缩区间。"""
        rng = self.range_size()
        new_high = self.low + rng * cum_high // total - 1
        new_low = self.low + rng * cum_low // total
        self.low, self.high = new_low, new_high

    def normalize(self):
        """重归一化：区间上界收敛时左移并读入新 bit。

        对应 libnative 里的区间比较 + 位读取循环。
        """
        while True:
            if self.high < (1 << (self.precision - 1)):
                pass                                    # 区间在上半
            elif self.low >= (1 << (self.precision - 1)):
                self.code -= 1 << (self.precision - 1)  # 区间在下半
                self.low -= 1 << (self.precision - 1)
                self.high -= 1 << (self.precision - 1)
            elif self.low >= (1 << (self.precision - 2)) and \
                 self.high < (1 << self.precision) - (1 << (self.precision - 2)):
                self.code -= 1 << (self.precision - 2)  # 区间跨越中点
                self.low -= 1 << (self.precision - 2)
                self.high -= 1 << (self.precision - 2)
            else:
                break
            self.low = (self.low << 1) & ((1 << self.precision) - 1)
            self.high = ((self.high << 1) | 1) & ((1 << self.precision) - 1)
            self.code = ((self.code << 1) | self.reader.get_bit()) & ((1 << self.precision) - 1)

    def current_fraction(self) -> float:
        return (self.code - self.low) / self.range_size()


# ----------------------------------------------------------------------
# body 解析
# ----------------------------------------------------------------------
def parse_body(payload: bytes):
    """拆出长度、种子、压缩数据段。"""
    if len(payload) < HEADER_LEN:
        raise ValueError("payload too short: %d < %d" % (len(payload), HEADER_LEN))
    declared = struct.unpack_from("<I", payload, 0)[0]
    seed = payload[SEED_OFF:SEED_OFF + SEED_LEN]
    tail16 = payload[SEED_OFF + SEED_LEN:HEADER_LEN]
    data = payload[HEADER_LEN:]
    return {
        "declared_len": declared,
        "seed": seed,
        "tail16": tail16,
        "data": data,
    }


def main():
    import glob
    import os

    for f in sorted(glob.glob("C:/FiddlerDump/lz4pairs/*_src.bin")):
        src = open(f, "rb").read()
        info = parse_body(src)
        print("\n=== %s ===" % os.path.basename(f))
        print("  declared_len = %d" % info["declared_len"])
        print("  seed     = %s" % info["seed"].hex(" "))
        print("  tail16   = %s" % info["tail16"].hex(" "))
        print("  数据段   = %d 字节  前16: %s"
              % (len(info["data"]), info["data"][:16].hex(" ")))

        state, inc = pcg_init(info["seed"])
        print("  PCG state=%#x inc=%#x" % (state, inc))
        ks = pcg_keystream(state, inc, 16)
        print("  PCG 前16字节 = %s" % ks.hex(" "))

        # 算术解码器还没接频率模型，这里只验证框架能初始化
        try:
            rd = RangeDecoder(BitReader(info["data"]))
            print("  RangeDecoder 初始化成功: low=%d high=%d code=%d 比例=%.4f"
                  % (rd.low, rd.high, rd.code, rd.current_fraction()))
        except Exception as exc:
            print("  RangeDecoder 初始化失败: %s" % exc)


if __name__ == "__main__":
    main()
