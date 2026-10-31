"""把 typedump.cs 的方法名/RVA 映射到 Ghidra 反编译产物。

Ghidra 从 GameAssembly_unpacked.dll 生成的 decompiled.c 里，函数都是 FUN_180xxxxxxx 形式。
typedump.cs 里有每个方法的真实名字和 RVA（ImageBase 相对）。
把它们对上，就能得到「带真实类名.方法名的伪代码」。

用法:
    python map_names_to_decompiled.py [--rebuild] [--extract METHOD]

产物:
    decompiled_named.c   把 FUN_1802580C10 替换成 Gallop_HorseOrderCalculator__UpdateHorseOrder
    funmap.json          RVA -> {class, method, signature} 的索引
    extract/<M>.c        指定方法的独立伪代码片段
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/Schwarz/projects/Hachimi-Edge")
TYPEDUMP = Path(r"C:/Users/Schwarz/uma_metadata/typedump.cs")
DECOMPILED = ROOT / "docs" / "decompiled.c"
OUT_DIR = Path(r"C:/Users/Schwarz/uma_metadata")
FUNMAP = OUT_DIR / "funmap.json"
NAMED_C = OUT_DIR / "decompiled_named.c"
IMGBASE = 0x180000000


def parse_typedump():
    """解析 typedump.cs，返回 {rva: {cls, method, ret, params}}"""
    print(f"[+] 解析 {TYPEDUMP.name} ({TYPEDUMP.stat().st_size:,} B)...")
    lines = TYPEDUMP.read_text(encoding="utf-8", errors="replace").split("\n")

    funmap = {}
    cls = None
    ns_stack = []
    for line in lines:
        s = line.strip()
        if s.startswith("public class "):
            m = re.match(r"public class ([\w\.\<\>\[\], ]+?)(?:\s*:\s*.+)?\s*//", s)
            if m:
                cls = m.group(1).strip()
        elif ";  // RVA 0x" in s:
            m = re.search(r"public (\S+) (\S+)\((\d+) args\);\s+// RVA 0x([0-9A-Fa-f]+)", s)
            if m and cls:
                ret, name, argc, rva = m.group(1), m.group(2), int(m.group(3)), int(m.group(4), 16)
                if rva == 0:
                    continue
                key = rva
                # 同一 RVA 会被多个方法共用（IL2CPP 的共享桩，比如很多 getter 返回 0）。
                # 桩的特征：类名是 <Module> / 以 < 开头，或者名字是 GetHashCode/Equals 等 Object 方法。
                def is_stub(c, mname):
                    if c.startswith("<") or ".<" in c:
                        return True
                    if mname in ("GetHashCode", "Equals", "ToString", "Finalize", "GetType"):
                        return True
                    return False

                cand = {"class": cls, "method": name, "ret": ret, "argc": argc}
                prev = funmap.get(key)
                if prev is None:
                    funmap[key] = cand
                elif is_stub(prev["class"], prev["method"]) and not is_stub(cls, name):
                    # 用非桩的覆盖桩
                    funmap[key] = cand
    print(f"    解析出 {len(funmap):,} 个有 RVA 的方法")
    return funmap


def safe_name(cls, method):
    """生成合法 C 标识符"""
    s = f"{cls}__{method}"
    s = re.sub(r"[^\w]", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def build_mapping(funmap):
    """RVA -> 替换后的函数名"""
    out = {}
    for rva, info in funmap.items():
        full = f"{IMGBASE + rva:x}"
        out[full] = safe_name(info["class"], info["method"])
    return out


def rewrite_decompiled(mapping):
    """分块重写 decompiled.c —— 逐行太慢，按 8 MB 块处理。"""
    import os
    print(f"[+] 重写 {DECOMPILED.name} ({DECOMPILED.stat().st_size:,} B)...")
    pat = re.compile(r"\bFUN_(1[0-9a-fA-F]{8})\b")
    total = DECOMPILED.stat().st_size
    n_repl = 0
    done = 0
    CHUNK = 8 * 1024 * 1024

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with DECOMPILED.open("r", encoding="utf-8", errors="replace", newline="") as fin, \
            NAMED_C.open("w", encoding="utf-8", newline="", buffering=1024*1024) as fout:
        carry = ""
        while True:
            chunk = fin.read(CHUNK)
            if not chunk:
                break
            buf = carry + chunk
            # 最后一行可能被截断，留到下一块
            cut = buf.rfind("\n")
            if cut < 0:
                carry = buf
                continue
            head, carry = buf[:cut+1], buf[cut+1:]

            def rep(m):
                nonlocal n_repl
                key = m.group(1).lower()
                nm = mapping.get(key)
                if nm is not None:
                    n_repl += 1
                    return nm
                return m.group(0)

            fout.write(pat.sub(rep, head))
            done += len(chunk)
            if done % (64 * 1024 * 1024) < CHUNK:
                print(f"    {done/1024/1024:.0f}/{total/1024/1024:.0f} MB, 替换 {n_repl:,} 处", flush=True)
        if carry:
            fout.write(pat.sub(rep, carry))

    print(f"    完成: 替换 {n_repl:,} 处")
    print(f"    输出: {NAMED_C}  ({NAMED_C.stat().st_size:,} B)")


def extract_method(name, funmap):
    """从 decompiled.c 抽出指定函数的完整伪代码"""
    # 先按方法名找 RVA
    targets = []
    for rva, info in funmap.items():
        if name.lower() in info["method"].lower() or name.lower() in info["class"].lower():
            targets.append((rva, info))

    if not targets:
        print(f"[x] 找不到方法名含 '{name}' 的")
        return

    print(f"[+] 找到 {len(targets)} 个匹配，抽取前 5 个")

    out_dir = OUT_DIR / "extract"
    out_dir.mkdir(parents=True, exist_ok=True)

    for rva, info in targets[:5]:
        full = f"0x{IMGBASE + rva:x}"
        # 在 decompiled.c 里找 `// FUN_xxxx @ 0x...` 注释
        funcname = f"FUN_{IMGBASE + rva:x}"
        found = []
        with DECOMPILED.open("r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                if funcname in line and "signature" not in line and "//" in line:
                    found.append(lineno)
                if lineno > 0 and found and lineno > found[0] + 5:
                    break

        if not found:
            print(f"  {info['class']}.{info['method']} (RVA 0x{rva:X}): decompiled.c 里没有")
            continue

        start = found[0]
        snippet = []
        with DECOMPILED.open("r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                if lineno < start - 3:
                    continue
                if lineno > start + 600:
                    break
                snippet.append(line.rstrip("\n"))
                if lineno > start + 5 and line.rstrip() == "}":
                    break

        fname = safe_name(info["class"], info["method"])
        p = out_dir / f"{fname}.c"
        header = (
            f"// {info['class']}.{info['method']}  ({info['ret']}, {info['argc']} args)\n"
            f"// RVA 0x{rva:X}  VA 0x{IMGBASE + rva:X}\n"
            f"// 来源: Ghidra 反编译 GameAssembly_unpacked.dll\n\n"
        )
        p.write_text(header + "\n".join(snippet), encoding="utf-8")
        print(f"  → {p}  ({len(snippet)} 行)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="重新生成 funmap.json 和 decompiled_named.c")
    ap.add_argument("--extract", help="抽取指定方法名的伪代码")
    args = ap.parse_args()

    if args.extract:
        if not FUNMAP.exists():
            print("[x] funmap.json 不存在，先跑一次不加参数")
            return 1
        funmap = {int(k): v for k, v in json.loads(FUNMAP.read_text(encoding="utf-8")).items()}
        extract_method(args.extract, funmap)
        return 0

    if not args.rebuild:
        print("用法: python map_names_to_decompiled.py --rebuild")
        print("      python map_names_to_decompiled.py --extract HorseOrderCalculator")
        return 0

    funmap = parse_typedump()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FUNMAP.write_text(json.dumps({str(k): v for k, v in funmap.items()},
                                  ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"[+] 写出 {FUNMAP}  ({FUNMAP.stat().st_size:,} B)")

    mapping = build_mapping(funmap)
    rewrite_decompiled(mapping)
    return 0


if __name__ == "__main__":
    sys.exit(main())
