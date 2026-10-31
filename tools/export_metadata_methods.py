"""导出 metadata 里的完整方法表，供定位 GA 函数用。

输出：
    C:/Users/Schwarz/uma_metadata/
        methods.tsv       typeIdx \t methodIndex \t ns.Class \t MethodName \t argCount
        types.tsv         typeIdx \t ns \t name \t methodStart \t methodCount
        lookup.txt        按 URL/Http/Base 关键字筛出的候选

字段布局（Il2CppTypeDefinition v31, stride 0x58）：
    +0x00 nameIndex
    +0x04 namespaceIndex
    +0x40 methodStart (u16)
    +0x42 methodCount (u16)
    +0x44 fieldStart  (u16)
    +0x46 fieldCount  (u16)

Il2CppMethodDefinition v31, stride 0x24：
    +0x00 nameIndex
    +0x04 declaringType (i32, typeIdx)
    +0x08 returnType    (i32)
    +0x0C parameterStart (u32)   （指向 parameters 表）
    +0x10 genericContainerIndex (i32)
    +0x14 token (u32)
    +0x18 flags (u16)
    +0x1A iflags (u16)
    +0x1C slot (u16)
    +0x22 parameterCount (u16)
"""
from __future__ import annotations

import os
import struct
import sys

META = r"C:/Users/Schwarz/projects/Hachimi-Edge/docs/metadata_jp_recovered.dat"
OUT = r"C:/Users/Schwarz/uma_metadata"

TD_STRIDE = 0x58
MD_STRIDE = 0x24


def main() -> int:
    d = open(META, "rb").read()
    pairs = [struct.unpack_from("<II", d, 8 + i * 8) for i in range(31)]
    str_off, str_size = pairs[2]
    strings = d[str_off:str_off + str_size]
    td_off, td_size = pairs[19]
    md_off, md_size = pairs[5]

    def rs(idx: int) -> str:
        if idx <= 0 or idx >= len(strings):
            return ""
        end = strings.find(b"\0", idx)
        if end < 0:
            return ""
        return strings[idx:end].decode("utf-8", "replace")

    os.makedirs(OUT, exist_ok=True)

    n_types = td_size // TD_STRIDE
    n_methods = md_size // MD_STRIDE
    print(f"types={n_types}  methods={n_methods}")

    # 先导出类型
    types = []
    for i in range(n_types):
        o = td_off + i * TD_STRIDE
        name = rs(struct.unpack_from("<I", d, o)[0])
        ns = rs(struct.unpack_from("<I", d, o + 4)[0])
        mstart, mcount = struct.unpack_from("<HH", d, o + 0x40)
        types.append((i, ns, name, mstart, mcount))

    with open(os.path.join(OUT, "types.tsv"), "w", encoding="utf-8") as fp:
        fp.write("typeIdx\tnamespace\tname\tmethodStart\tmethodCount\n")
        for t in types:
            fp.write("%d\t%s\t%s\t%d\t%d\n" % t)

    # 再导出方法
    rows = []
    for i in range(n_methods):
        o = md_off + i * MD_STRIDE
        name_idx = struct.unpack_from("<I", d, o)[0]
        decl = struct.unpack_from("<i", d, o + 4)[0]
        argc = struct.unpack_from("<H", d, o + 0x22)[0]
        name = rs(name_idx)
        if not name:
            continue
        if 0 <= decl < n_types:
            _, ns, tname, _, _ = types[decl]
            full = f"{ns}.{tname}" if ns else tname
        else:
            full = f"<bad:{decl}>"
        rows.append((decl, i, full, name, argc))

    with open(os.path.join(OUT, "methods.tsv"), "w", encoding="utf-8") as fp:
        fp.write("typeIdx\tmethodIndex\tclass\tmethod\targCount\n")
        for r in rows:
            fp.write("%d\t%d\t%s\t%s\t%d\n" % r)

    # 候选：URL / Http / Base 相关
    keys = ("url", "http", "base", "send", "request", "api")
    with open(os.path.join(OUT, "lookup.txt"), "w", encoding="utf-8") as fp:
        for decl, idx, cls, name, argc in rows:
            low = (cls + "." + name).lower()
            if any(k in low for k in keys):
                fp.write("%s\t%s\targc=%d\tmethodIndex=%d\n" % (cls, name, argc, idx))

    # 统计
    with open(os.path.join(OUT, "lookup.txt"), "r", encoding="utf-8") as fp:
        cand = sum(1 for _ in fp)
    print(f"methods.tsv  {len(rows)} 行")
    print(f"lookup.txt   {cand} 行")
    print(f"输出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
