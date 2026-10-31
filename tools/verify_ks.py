"""验证 ksout 里的密钥流块能否解出样本。

思路：
  对每个 ctrsample，算 keystream_expected = in XOR out
  然后在 ksout 序列里滑动搜索，看哪一段连续块能匹配
"""
from __future__ import annotations

import glob
import os

KS_DIR = r"C:/Users/Schwarz/ksout"
CTR_DIR = r"C:/Users/Schwarz/ctrsamples"


def load_ks():
    files = sorted(glob.glob(os.path.join(KS_DIR, "*_ks.bin")))
    return [open(f, "rb").read() for f in files]


def main():
    ks_blocks = load_ks()
    print(f"密钥流块 {len(ks_blocks)} 个，每块 {len(ks_blocks[0]) if ks_blocks else 0} 字节")

    idxs = sorted({os.path.basename(f)[:2] for f in glob.glob(os.path.join(CTR_DIR, "*_in.bin"))})
    print(f"样本 {len(idxs)} 组\n")

    for idx in idxs:
        i = open(os.path.join(CTR_DIR, f"{idx}_in.bin"), "rb").read()
        o = open(os.path.join(CTR_DIR, f"{idx}_out.bin"), "rb").read()
        exp = bytes(a ^ b for a, b in zip(i, o))

        need = (len(exp) + 15) // 16
        print(f"=== {idx}: len={len(exp)} 需要 {need} 块 ===")
        print(f"  expected[0:16] = {exp[:16].hex()}")

        found = -1
        # 用前三块做匹配，避免全扫
        pat = exp[:48]
        for start in range(0, len(ks_blocks) - 2):
            cat = ks_blocks[start] + ks_blocks[start+1] + ks_blocks[start+2]
            if cat[:48] == pat:
                found = start
                break

        if found >= 0:
            print(f"  ★★★ 找到匹配起点 block#{found}")
            # 拼接完整
            buf = b"".join(ks_blocks[found:found+need])
            if buf[:len(exp)] == exp:
                print(f"  ★★★ 完整匹配！密钥流可以解密该样本")
            else:
                print(f"  前缀匹配但全长不符")
        else:
            print(f"  （未找到匹配起点）")
        print()


if __name__ == "__main__":
    main()
