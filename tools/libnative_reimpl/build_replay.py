"""把 umacap/ 里录到的响应编成本地回放库。

产出 replay.json：
    {
      "entries": [
        {"key": <明文长度>, "seq": 0, "dst": "0000_resp_dst.bin", "len": 526,
         "src_len": 397, "head": "<前32字节hex>"}
      ]
    }

匹配策略（按可靠性排序）：
  1. 明文长度 declared（src[0:4]）—— 唯一且稳定
  2. 同一长度出现多次时，按调用顺序取
  3. 兜底：原样放行给真实实现
"""
from __future__ import annotations

import glob
import json
import os
import struct
import sys

CAP_DIR = r"C:/Users/Schwarz/umacap"
OUT = os.path.join(CAP_DIR, "replay.json")


def main() -> int:
    entries = []
    for f in sorted(glob.glob(os.path.join(CAP_DIR, "*_resp_hdr.bin"))):
        seq = os.path.basename(f)[:4]
        hdr = open(f, "rb").read()
        dstf = os.path.join(CAP_DIR, f"{seq}_resp_dst.bin")
        srcf = os.path.join(CAP_DIR, f"{seq}_resp_src.bin")
        if not os.path.exists(dstf):
            continue
        if len(hdr) < 4:
            print(f"  {seq}: hdr 太短，跳过")
            continue
        declared = struct.unpack_from("<I", hdr, 0)[0]
        dst_len = os.path.getsize(dstf)
        src_len = os.path.getsize(srcf) if os.path.exists(srcf) else 0
        entries.append({
            "key": declared,
            "seq": int(seq),
            "dst": os.path.basename(dstf),
            "len": dst_len,
            "src_len": src_len,
            "head": hdr.hex(),
        })
        print(f"  {seq}: declared={declared:>8}  dst={dst_len:>8}  src={src_len:>8}")

    # 检查 key 冲突
    seen = {}
    for e in entries:
        seen.setdefault(e["key"], []).append(e["seq"])
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        print(f"\n注意：有 {len(dup)} 个长度出现多次（需按顺序匹配）：{dict(list(dup.items())[:5])}")

    payload = {"entries": entries, "count": len(entries)}
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    print(f"\n写出 {OUT}，共 {len(entries)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
