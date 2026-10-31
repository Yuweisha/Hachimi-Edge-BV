"""离线解包 libnative 的响应 body。

用法：
    python decode_body.py <src.bin>            # 直接从 src 解（需要 lz4in 已生成）
    python decode_body.py --lz4in <lz4in.bin>  # 直接解 LZ4 流
    python decode_body.py --dir <目录>          # 批量

原理（已在实机验证）：
    插件 hook libnative+0x143210 返回后，按 ret（消耗的输入字节数）
    落盘的是**解密后的标准 LZ4 block**，用 lz4.block 直接解即可得到 msgpack。

    原始 src 布局（36 字节头）：
        [0:4]   明文长度 LE
        [4:36]  32 字节密钥材料（每请求不同）
        [36:]   加密后的 LZ4 流

    src[36:] -> lz4in 之间的变换（流密码）尚未复刻，
    所以本脚本需要插件产出的 lz4in，不能只凭 src 独立解码。
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

try:
    import lz4.block as lz4b
except ImportError:
    lz4b = None

try:
    import msgpack
except ImportError:
    msgpack = None


def decode_lz4(data: bytes, declared: int | None = None) -> bytes:
    """解标准 LZ4 block。declared 为 None 时逐级尝试常见长度。"""
    if lz4b is None:
        raise RuntimeError("需要 pip install lz4")
    sizes = []
    if declared:
        sizes.append(declared)
    sizes += [526, 925, 903, 51413, 1200869, 1200897]
    for s in sizes:
        try:
            return lz4b.decompress(data, uncompressed_size=s)
        except Exception:
            continue
    try:
        return lz4b.decompress(data)
    except Exception as e:
        raise RuntimeError(f"LZ4 解压失败: {e}") from e


def unpack_msgpack(raw: bytes):
    if msgpack is None:
        return None
    try:
        return msgpack.unpackb(raw, raw=False, strict_map_key=False)
    except Exception:
        return None


def show(raw: bytes) -> None:
    print(f"  明文 {len(raw)} 字节")
    print(f"  前 32 字节: {raw[:32].hex()}")
    obj = unpack_msgpack(raw)
    if obj is None:
        print("  (msgpack 解析失败，仅输出原始字节)")
        return
    if isinstance(obj, dict):
        print(f"  msgpack 顶层键 ({len(obj)}): {list(obj.keys())[:12]}")
        if "response_code" in obj:
            print(f"  response_code = {obj['response_code']}")
        data = obj.get("data")
        if isinstance(data, dict):
            print(f"  data 键数 = {len(data)}")
    else:
        print(f"  msgpack 类型: {type(obj).__name__}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help="src.bin（36 字节头 + 加密 LZ4 流）")
    ap.add_argument("--lz4in", help="已解密的 LZ4 流")
    ap.add_argument("--dir", help="批量处理目录（找 *_src.bin 与同名 .bin）")
    args = ap.parse_args()

    if args.dir:
        d = args.dir
        n = 0
        for f in sorted(os.listdir(d)):
            if not f.endswith(".bin") or f.endswith("_src.bin"):
                continue
            base = f[:-4]
            lf = os.path.join(d, f)
            sf = os.path.join(d, base + "_src.bin")
            if not os.path.exists(sf):
                continue
            src = open(sf, "rb").read()
            lz = open(lf, "rb").read()
            if len(src) - len(lz) != 36:
                continue
            declared = struct.unpack_from("<I", src, 0)[0]
            print(f"=== {base}: src={len(src)} lz4in={len(lz)} declared={declared} ===")
            try:
                show(decode_lz4(lz, declared))
            except Exception as e:
                print(f"  失败: {e}")
            n += 1
        print(f"\n共处理 {n} 组")
        return 0

    if args.lz4in:
        data = open(args.lz4in, "rb").read()
        show(decode_lz4(data))
        return 0

    if not args.src:
        ap.print_help()
        return 1

    # 只有 src：尝试用前缀同名的 .bin
    src = open(args.src, "rb").read()
    declared = struct.unpack_from("<I", src, 0)[0]
    guess = args.src.replace("_src.bin", ".bin")
    if os.path.exists(guess) and len(src) - os.path.getsize(guess) == 36:
        print(f"=== 用配对文件 {os.path.basename(guess)} ===")
        show(decode_lz4(open(guess, "rb").read(), declared))
        return 0

    print("只给了 src，缺少解密后的 LZ4 流。")
    print("选项：")
    print("  1. 用插件跑一次，产出 lz4in/ 后再用 --dir 批量解")
    print("  2. 用 --lz4in 指定已解密的流")
    print("  3. src[36:] 仍是加密态，离线变换尚未复刻")
    return 2


if __name__ == "__main__":
    sys.exit(main())
