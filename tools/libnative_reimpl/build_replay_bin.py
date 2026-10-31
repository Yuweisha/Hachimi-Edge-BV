"""生成插件可直接读取的回放库（无 JSON 依赖）。

扫描 umacap/，把每组 (srcSize, declared) -> 明文写出：

    umacap/replay.bin
        魔数 "RPLY"(4) + u32 条数
        每项: u32 srcSize + u32 declared + u32 dataLen + data

以及索引文件 replay_idx.txt（人类可读，便于核对）。
"""
from __future__ import annotations

import glob
import os
import struct
import sys

CAP_DIR = r"C:/Users/Schwarz/umacap"
OUT_BIN = os.path.join(CAP_DIR, "replay.bin")
OUT_TXT = os.path.join(CAP_DIR, "replay_idx.txt")


def main() -> int:
    items = []
    for hdr_path in sorted(glob.glob(os.path.join(CAP_DIR, "*_resp_hdr.bin"))):
        seq = os.path.basename(hdr_path)[:4]
        dst_path = os.path.join(CAP_DIR, f"{seq}_resp_dst.bin")
        src_path = os.path.join(CAP_DIR, f"{seq}_resp_src.bin")
        if not os.path.exists(dst_path):
            continue
        hdr = open(hdr_path, "rb").read()
        if len(hdr) < 4:
            continue
        declared = struct.unpack_from("<I", hdr, 0)[0]
        dst = open(dst_path, "rb").read()
        src_size = os.path.getsize(src_path) if os.path.exists(src_path) else 0
        items.append((src_size, declared, dst, seq))

    if not items:
        print("没有可用的录制样本")
        return 1

    with open(OUT_BIN, "wb") as fp:
        fp.write(b"RPLY")
        fp.write(struct.pack("<I", len(items)))
        for src_size, declared, data, _ in items:
            fp.write(struct.pack("<III", src_size, declared, len(data)))
            fp.write(data)

    with open(OUT_TXT, "w", encoding="utf-8") as fp:
        fp.write(f"# {len(items)} 条\n")
        fp.write(f"# {'seq':<6}{'srcSize':>10}{'declared':>12}{'dataLen':>12}\n")
        for src_size, declared, data, seq in items:
            fp.write(f"  {seq:<6}{src_size:>10}{declared:>12}{len(data):>12}\n")

    print(f"写出 {OUT_BIN} ({os.path.getsize(OUT_BIN)} 字节)，{len(items)} 条")
    for src_size, declared, data, seq in items:
        print(f"  {seq}: srcSize={src_size:>8} declared={declared:>9} len={len(data):>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
