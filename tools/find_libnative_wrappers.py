"""定位 LibNative.* 托管包装，并把 methodIndex 映射到真实 RVA。

思路：
  1. 从 metadata 找出 namespace 或类名含 LibNative 的类型
  2. 拿它们的 methodStart/methodCount，列出方法名 + 参数数
  3. 用 methodPointers 数组把 methodIndex 换成 RVA
  4. 判断 RVA 落在 GameAssembly 的 il2cpp 节（0x491000..0x62b0000）
     还是别处（说明是 P/Invoke thunk，真正的实现在 libnative.dll）
"""
from __future__ import annotations

import struct
import sys

META = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/metadata_jp_recovered.dat"
GA = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/GameAssembly_unpacked.dll"

IB_RUNTIME = 0x7FF9F2A10000        # GameAssembly 运行基址（已由 HttpHelper.Send 验证）
ARR_RVA = 0x069A3ED0               # methodPointers
TD_STRIDE = 0x58
MD_STRIDE = 0x24

IL2CPP_LO = 0x00491000
IL2CPP_HI = 0x062B0000


def main() -> int:
    d = open(META, "rb").read()
    pairs = [struct.unpack_from("<II", d, 8 + i * 8) for i in range(31)]
    strings = d[pairs[2][0]:pairs[2][0] + pairs[2][1]]
    td_off, td_size = pairs[19]
    md_off, md_size = pairs[5]

    ga = open(GA, "rb").read()

    def rs(idx: int) -> str:
        if idx <= 0 or idx >= len(strings):
            return ""
        e = strings.find(b"\0", idx)
        return strings[idx:e].decode("utf-8", "replace") if e > 0 else ""

    n_types = td_size // TD_STRIDE
    n_methods = md_size // MD_STRIDE

    # 收集 LibNative 类型
    targets = []
    for i in range(n_types):
        o = td_off + i * TD_STRIDE
        name = rs(struct.unpack_from("<I", d, o)[0])
        ns = rs(struct.unpack_from("<I", d, o + 4)[0])
        if "libnative" in (ns + "." + name).lower() or "libnative" in ns.lower():
            mstart, mcount = struct.unpack_from("<HH", d, o + 0x40)
            targets.append((i, ns, name, mstart, mcount))

    if not targets:
        print("没有 LibNative.* 类型")
        return 1

    print(f"找到 {len(targets)} 个 LibNative 类型\n")

    for tidx, ns, name, mstart, mcount in targets:
        print(f"=== {ns}.{name}  (typeIdx={tidx}, methods={mcount}) ===")
        for k in range(mcount):
            midx = mstart + k
            if midx >= n_methods:
                break
            mo = md_off + midx * MD_STRIDE
            mn = rs(struct.unpack_from("<I", d, mo)[0])
            argc = struct.unpack_from("<H", d, mo + 0x22)[0]

            # 映射 RVA
            ptr = struct.unpack_from("<Q", ga, ARR_RVA + midx * 8)[0]
            rva = ptr - IB_RUNTIME if ptr > IB_RUNTIME else 0
            zone = "?"
            if rva and IL2CPP_LO <= rva < IL2CPP_HI:
                zone = "il2cpp(托管实现)"
            elif rva:
                zone = "其他节"
            else:
                zone = "未映射"

            print(f"  {mn:<28} argc={argc:<2} midx={midx:<7} ptr=0x{ptr:x} rva=0x{rva:x}  {zone}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
