"""把 local_server.py 和 admin_ui.py 的硬编码路径改成「exe 同目录优先」。

Nuitka onefile 运行时：
  sys.executable  = exe 的绝对路径
  __file__        = 临时解压目录（不要用）

所以基准目录 = os.path.dirname(sys.executable)（打包后）或脚本所在目录的上级（源码运行）。
"""
import io
import re

# ---------- local_server.py ----------
P1 = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
s = io.open(P1, encoding="utf-8").read()

# 1) 在 import 之后插入 base_dir 解析
anchor = '''# 同目录 import（打包成 exe 后也能用）'''
assert anchor in s

helper = '''# 数据目录：exe 同目录优先，退回开发机路径
def _resolve_base() -> str:
    import sys as _sys
    if getattr(_sys, "frozen", False) or "__compiled__" in globals():
        # Nuitka onefile：sys.executable 指向 exe
        return os.path.dirname(os.path.abspath(_sys.executable))
    here = os.path.dirname(os.path.abspath(__file__))
    # 源码运行：tools/ 的上一级
    parent = os.path.dirname(here)
    if os.path.isdir(os.path.join(parent, "uma_replay")) or os.path.exists(
        os.path.join(parent, "uma_replay", "replay.bin")
    ):
        return os.path.join(parent, "uma_replay")
    # 再试 exe 同目录（打包后 exe 就在数据旁边）
    if os.path.exists(os.path.join(here, "replay.bin")):
        return here
    return r"C:/Users/Schwarz/uma_replay"


BASE_DIR = _resolve_base()

# 同目录 import（打包成 exe 后也能用）'''

s = s.replace(anchor, helper, 1)

# 2) 替换所有硬编码路径
s = s.replace('DB = r"C:/Users/Schwarz/uma_replay"', 'DB = BASE_DIR')
s = s.replace('"C:/Users/Schwarz/uma_replay/req"', 'os.path.join(BASE_DIR, "req")')
s = s.replace('"C:/Users/Schwarz/uma_replay/raw"', 'os.path.join(BASE_DIR, "raw")')
s = s.replace('"C:/Users/Schwarz/uma_replay/path_declared.json"',
              'os.path.join(BASE_DIR, "path_declared.json")')
s = s.replace('REQPLAIN_DIR = "C:/Users/Schwarz/uma_replay/reqplain"',
              'REQPLAIN_DIR = os.path.join(BASE_DIR, "reqplain")')
s = s.replace('DYNAMIC_DIR = "C:/Users/Schwarz/uma_replay/dynamic"',
              'DYNAMIC_DIR = os.path.join(BASE_DIR, "dynamic")')
s = s.replace('Path("C:/Users/Schwarz/uma_replay/gacha.json")',
              'Path(os.path.join(BASE_DIR, "gacha.json"))')
s = s.replace('"C:/Users/Schwarz/uma_replay/gacha.json"',
              'os.path.join(BASE_DIR, "gacha.json")')
s = s.replace('"C:/Users/Schwarz/uma_replay/locked_paths.json"',
              'os.path.join(BASE_DIR, "locked_paths.json")')
s = s.replace('"C:/Users/Schwarz/uma_replay/dynamic"',
              'os.path.join(BASE_DIR, "dynamic")')

io.open(P1, "w", encoding="utf-8", newline="\n").write(s)
print("local_server.py 已改")

# 检查剩余
left = [l for l in s.split("\n") if "C:/Users/Schwarz/uma_replay" in l
        and "return r" not in l and "BASE_DIR" not in l]
print(f"  剩余硬编码: {len(left)}")
for l in left[:5]:
    print(f"    {l.strip()}")

# ---------- admin_ui.py ----------
P2 = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/admin_ui.py"
s2 = io.open(P2, encoding="utf-8").read()

s2 = s2.replace('REPLAY = r"C:/Users/Schwarz/uma_replay"', 'REPLAY = BASE_DIR')
s2 = s2.replace('"C:/Users/Schwarz/uma_replay"', 'BASE_DIR')

# 如果 admin_ui 里没有 BASE_DIR，从 local_server 导入
if "BASE_DIR" in s2 and "from local_server import" not in s2 and "BASE_DIR =" not in s2.split("\n")[0:20]:
    # 在 import 段后插入兜底定义
    m = re.search(r"^(import |from )", s2, re.M)
    if m:
        ins = m.start()
        fallback = '''# 数据目录（未从 local_server 导入时自行解析）
try:
    from local_server import BASE_DIR  # type: ignore
except Exception:
    import sys as _sys, os as _os
    if getattr(_sys, "frozen", False) or "__compiled__" in globals():
        BASE_DIR = _os.path.dirname(_os.path.abspath(_sys.executable))
    else:
        BASE_DIR = r"C:/Users/Schwarz/uma_replay"

'''
        s2 = s2[:ins] + fallback + s2[ins:]

io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("admin_ui.py 已改")
left2 = [l for l in s2.split("\n") if "C:/Users/Schwarz/uma_replay" in l]
print(f"  剩余硬编码: {len(left2)}")
for l in left2[:5]:
    print(f"    {l.strip()}")
