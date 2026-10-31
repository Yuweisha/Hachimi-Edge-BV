"""从 typedump.cs 生成 Il2CppDumper 兼容的 script.json + il2cpp.h。

用途：dumper 本体跑不起来（CodeRegistration 在堆上），但 IDA 脚本
（ida_with_struct_py3.py）只需要这两个文件的格式，内容可以自己造。

用法:
    python gen_ida_script.py

产物:
    script.json     IDAPython 脚本读它给函数改名
    il2cpp.h        结构体定义（IDA 里 ApplyStruct）
"""
import json
import re
import sys
from pathlib import Path

TYPEDUMP = Path(r"C:/Users/Schwarz/uma_metadata/typedump.cs")
OUT_DIR = Path(r"C:/Users/Schwarz/uma_metadata")
SCRIPT_JSON = OUT_DIR / "script.json"
IL2CPP_H = OUT_DIR / "il2cpp.h"
IMGBASE = 0x180000000

# 这些字符在 IDA 名字里非法，统一替换
NAME_SAFE = re.compile(r"[^\w\.\$\@\?]")


def parse_typedump():
    """返回 classes: {full_name: {fields: [...], methods: [...]}}"""
    print(f"[+] 解析 {TYPEDUMP.name} ({TYPEDUMP.stat().st_size:,} B)...")
    classes = {}
    cur = None
    lines = TYPEDUMP.read_text(encoding="utf-8", errors="replace").split("\n")
    for line in lines:
        s = line.strip()
        if s.startswith("public class "):
            m = re.match(
                r"public class ([\w\.\<\>\[\], ]+?)(?:\s*:\s*([\w\.\<\>\[\], ]+))?\s*//\s*flags=0x([0-9A-Fa-f]+)",
                s)
            if m:
                full, parent, flags = m.group(1).strip(), (m.group(2) or "").strip(), int(m.group(3), 16)
                cur = {"parent": parent, "flags": flags, "fields": [], "methods": []}
                classes[full] = cur
            continue
        if cur is None:
            continue
        # 字段：public <type> <name>;  // +0xNN
        mf = re.match(r"public (\S+) (\S+);\s+// \+0x([0-9A-Fa-f]+)", s)
        if mf:
            cur["fields"].append({"type": mf.group(1), "name": mf.group(2), "off": int(mf.group(3), 16)})
            continue
        # 方法：public <ret> <name>(N args);  // RVA 0xNNN
        mm = re.match(r"public (\S+) (\S+)\((\d+) args\);\s+// RVA 0x([0-9A-Fa-f]+)", s)
        if mm:
            cur["methods"].append({
                "ret": mm.group(1), "name": mm.group(2),
                "argc": int(mm.group(3)), "rva": int(mm.group(4), 16),
            })
    print(f"    解析出 {len(classes):,} 个类")
    return classes


def cxx_type(t, classes):
    """C# 类型名 -> il2cpp.h 里用的类型名"""
    prim = {
        "System.Void": "void", "System.Boolean": "bool", "System.Byte": "uint8_t",
        "System.SByte": "int8_t", "System.Char": "uint16_t", "System.Int16": "int16_t",
        "System.UInt16": "uint16_t", "System.Int32": "int32_t", "System.UInt32": "uint32_t",
        "System.Int64": "int64_t", "System.UInt64": "uint64_t", "System.Single": "float",
        "System.Double": "double", "System.String": "String_t*", "System.Object": "Il2CppObject*",
    }
    if t in prim:
        return prim[t]
    if t.endswith("[]"):
        inner = cxx_type(t[:-2], classes)
        return f"Il2CppArray* /* {inner}[] */"
    if t.startswith("System.Collections.Generic.List<"):
        return "Il2CppObject* /* List */"
    if t.startswith("System.Collections.Generic.Dictionary<"):
        return "Il2CppObject* /* Dictionary */"
    if t in classes:
        safe = re.sub(r"[^\w]", "_", t)
        return f"{safe}_o*"
    # 值类型 / 未知：当结构体
    if t in ("System.ValueType",):
        return "Il2CppObject*"
    safe = re.sub(r"[^\w]", "_", t)
    return f"{safe}_o"


def gen_il2cpp_h(classes):
    print(f"[+] 生成 {IL2CPP_H.name}...")
    out = [
        "// 由 typedump.cs 生成 —— 供 IDA 的 il2cpp 脚本使用",
        "#pragma once",
        "#include <stdint.h>",
        "",
        "typedef struct Il2CppObject Il2CppObject;",
        "typedef struct Il2CppArray Il2CppArray;",
        "typedef struct String_t String_t;",
        "typedef struct Il2CppClass Il2CppClass;",
        "typedef struct MethodInfo MethodInfo {",
        "    void* methodPointer;",
        "    void* virtualMethodPointer;",
        "    void* invoker_method;",
        "    const char* name;",
        "    Il2CppClass* klass;",
        "} MethodInfo;",
        "",
    ]

    # 按 size 排序（小结构体先定义，避免前向引用问题）
    def size_of(ci):
        if not ci["fields"]:
            return 0
        return max(f["off"] for f in ci["fields"]) + 8

    ordered = sorted(classes.items(), key=lambda kv: size_of(kv[1]))

    count = 0
    for full, ci in ordered:
        if not ci["fields"]:
            continue
        safe = re.sub(r"[^\w]", "_", full)
        out.append(f"// {full}  (flags=0x{ci['flags']:X})")
        out.append(f"typedef struct {safe}_o {{")
        if ci["parent"] and ci["parent"] != "System.Object":
            psafe = re.sub(r"[^\w]", "_", ci["parent"])
            out.append(f"    {psafe}_o __base;")
        elif ci["parent"] in ("System.Object", ""):
            out.append("    Il2CppObject __base;")
        for f in sorted(ci["fields"], key=lambda x: x["off"]):
            ct = cxx_type(f["type"], classes)
            out.append(f"    {ct} {f['name']};  // +0x{f['off']:X}")
        out.append(f"}} {safe}_o;")
        out.append("")
        count += 1

    IL2CPP_H.parent.mkdir(parents=True, exist_ok=True)
    IL2CPP_H.write_text("\n".join(out), encoding="utf-8")
    print(f"    {count} 个结构体, {IL2CPP_H.stat().st_size:,} B")


def gen_script_json(classes):
    """ScriptMethod：给 IDA 里的函数改名 + 加签名"""
    print(f"[+] 生成 {SCRIPT_JSON.name}...")

    # RVA -> 方法（同 RVA 多方法时保留第一个非桩）
    by_rva = {}
    for full, ci in classes.items():
        cls_safe = full
        for m in ci["methods"]:
            rva = m["rva"]
            if rva == 0:
                continue
            name = f"{cls_safe}$${m['name']}"
            if rva in by_rva:
                continue
            by_rva[rva] = (name, full, m)

    script_method = []
    for rva, (name, full, m) in sorted(by_rva.items()):
        va = IMGBASE + rva
        ret = cxx_type(m["ret"], classes)
        this_t = re.sub(r"[^\w]", "_", full) + "_o*"
        params = [f"{this_t} __this"]
        for i in range(m["argc"]):
            params.append(f"void* __arg{i}")
        params.append("const MethodInfo* method")
        sig_name = re.sub(r"[^\w]", "_", name)
        sig = f"{ret} {sig_name} ({', '.join(params)})"
        script_method.append({
            "Address": va,
            "Name": NAME_SAFE.sub("_", name),
            "Signature": sig,
        })

    doc = {
        "ScriptMethod": script_method,
        "ScriptString": [],
        "Addresses": [{"Address": va, "Name": nm} for va, nm in
                       ((IMGBASE + r, n[0]) for r, n in sorted(by_rva.items()))],
    }

    SCRIPT_JSON.parent.mkdir(parents=True, exist_ok=True)
    SCRIPT_JSON.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(f"    ScriptMethod {len(script_method):,} 条, {SCRIPT_JSON.stat().st_size:,} B")


def main():
    classes = parse_typedump()
    gen_il2cpp_h(classes)
    gen_script_json(classes)
    print(f"\n[+] 产物:")
    print(f"    {SCRIPT_JSON}")
    print(f"    {IL2CPP_H}")
    print(f"\n在 IDA 里：File -> Script file -> 选 Il2CppDumper 的 ida_with_struct_py3.py")
    print(f"脚本会问 script.json / il2cpp.h 路径，指到上面两个文件即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
