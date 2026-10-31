"""修复三处开关不一致：
1. admin_ui.py 的 SWITCHES["intercept"] 改为 umalib.json 的 offline 字段
2. /api/mode 写 umalib.json（插件读这个）
3. 剩余硬编码路径改相对
"""
import io
import re

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/admin_ui.py"
s = io.open(P, encoding="utf-8").read()

# ---- 1) 加 umalib.json 读写工具 ----
anchor = "REPLAY = BASE_DIR"
assert anchor in s

helpers = '''REPLAY = BASE_DIR
UMALIB_CFG = os.path.join(BASE_DIR, "umalib.json")


def _umalib_get(key: str):
    """读 umalib.json 的布尔/字符串字段（插件的第一优先级配置）。"""
    try:
        with open(UMALIB_CFG, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get(key)
    except Exception:
        return None


def _umalib_set(**kw):
    """写 umalib.json（保留其它字段）。"""
    d = {}
    try:
        with open(UMALIB_CFG, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.update(kw)
    try:
        os.makedirs(os.path.dirname(UMALIB_CFG), exist_ok=True)
        with open(UMALIB_CFG, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

'''
s = s.replace(anchor, helpers, 1)

# ---- 2) SWITCHES 里的 intercept 改为虚拟键（由 status/toggle 特判）----
s = s.replace('''SWITCHES = {
    "intercept": os.path.join(REPLAY, "intercept.on"),
    "mark": os.path.join(REPLAY, "mark.on"),
    "ksdump": r"C:/Users/Schwarz/ksdump.on",
    "urlpatch_off": r"C:/Users/Schwarz/urlpatch.off",
}''', '''SWITCHES = {
    # intercept 不再是文件：由 umalib.json 的 offline 字段控制（插件第一优先级）
    "intercept": None,
    "mark": os.path.join(REPLAY, "mark.on"),
    "ksdump": os.path.join(REPLAY, "ksdump.on"),
    "urlpatch_off": os.path.join(REPLAY, "urlpatch.off"),
}
# 插件数据目录（key 文件放这里）
HACHIMI_DATA = os.environ.get("UMALIB_DATA_DIR", REPLAY)''')

# ---- 3) 硬编码日志/工具路径改相对 ----
s = s.replace('LOG = r"C:/Users/Schwarz/localsrv.log"', 'LOG = os.path.join(BASE_DIR, "localsrv.log")')
s = s.replace('TOOLS = r"C:/Users/Schwarz/projects/Hachimi-Edge/tools"',
              'TOOLS = os.path.dirname(os.path.abspath(__file__))')
s = s.replace('PYEXE = r"C:/Users/Schwarz/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"',
              'PYEXE = sys.executable')

# ---- 4) toggle 特判 intercept ----
old_toggle = '''        p = SWITCHES[name]
        if os.path.exists(p):
            os.remove(p)
        else:
            open(p, "w").close()
        return 200, "application/json", json.dumps(status(), ensure_ascii=False).encode()'''
new_toggle = '''        if name == "intercept":
            cur = _umalib_get("offline")
            if cur is None:
                cur = os.path.exists(os.path.join(REPLAY, "intercept.on"))
            _umalib_set(offline=not cur)
            # 同步文件哨兵，兼容旧版插件
            sentinel = os.path.join(REPLAY, "intercept.on")
            if cur:
                try:
                    os.remove(sentinel)
                except Exception:
                    pass
            else:
                try:
                    open(sentinel, "w").close()
                except Exception:
                    pass
        else:
            p = SWITCHES[name]
            if os.path.exists(p):
                os.remove(p)
            else:
                open(p, "w").close()
        return 200, "application/json", json.dumps(status(), ensure_ascii=False).encode()'''
assert old_toggle in s
s = s.replace(old_toggle, new_toggle, 1)

# ---- 5) /api/mode 改为写 umalib.json ----
old_mode = '''        mode = (query.get("mode") or [""])[0]
        if mode == "online":
            for p in (SWITCHES["intercept"], SWITCHES["urlpatch_off"], SWITCHES["mark"]):
                if os.path.exists(p):
                    os.remove(p)
        elif mode == "local":
            open(SWITCHES["intercept"], "w").close()
            if os.path.exists(SWITCHES["urlpatch_off"]):
                os.remove(SWITCHES["urlpatch_off"])
        else:
            return 400, "application/json", b'{"error":"bad mode"}''
new_mode = '''        mode = (query.get("mode") or [""])[0]
        sentinel = os.path.join(REPLAY, "intercept.on")
        if mode == "online":
            # 在线录制：插件不拦截，走真服务器
            _umalib_set(offline=False)
            for p in (sentinel, SWITCHES["urlpatch_off"], SWITCHES["mark"]):
                if p and os.path.exists(p):
                    os.remove(p)
            # 在线录制必须开请求落盘
            for k in ("ctrdump.on",):
                kp = os.path.join(REPLAY, k)
                if not os.path.exists(kp):
                    open(kp, "w").close()
        elif mode == "local":
            # 离线回放：插件拦截
            _umalib_set(offline=True)
            try:
                open(sentinel, "w").close()
            except Exception:
                pass
            if SWITCHES["urlpatch_off"] and os.path.exists(SWITCHES["urlpatch_off"]):
                os.remove(SWITCHES["urlpatch_off"])
        else:
            return 400, "application/json", b'{"error":"bad mode"}'
"""
assert old_mode in s
s = s.replace(old_mode, new_mode, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("admin_ui.py 已改")
left = [l.strip() for l in s.split("\n") if "C:/Users/Schwarz" in l]
print(f"剩余硬编码: {len(left)}")
for l in left:
    print(f"  {l}")
