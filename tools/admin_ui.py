"""离线服务器的插件 API（/api/offline、/api/switches、/api/config）。

挂载到 local_server.py：
    from admin_ui import handle_api
"""
from __future__ import annotations

# 数据目录（未从 local_server 导入时自行解析）
try:
    from local_server import BASE_DIR  # type: ignore
except Exception:
    import sys as _sys, os as _os
    if getattr(_sys, "frozen", False) or "__compiled__" in globals():
        BASE_DIR = _os.path.dirname(_os.path.abspath(_sys.executable))
    else:
        BASE_DIR = r"C:/Users/Schwarz/uma_replay"

import json
import os
import subprocess
import sys
import time

REPLAY = BASE_DIR
REPLAY_BIN = os.path.join(REPLAY, "replay.bin")
DECL_JSON = os.path.join(REPLAY, "path_declared.json")

GAME_DIR = os.environ.get("UMA_GAME_DIR",
                          r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn")
GAME_EXE = os.path.join(GAME_DIR, "UmamusumePrettyDerby_Jpn.exe")


def _umalib_cfg_path() -> str:
    """插件实际读取的 umalib.json：优先 <游戏>/hachimi/umalib.json。"""
    cands = []
    env = os.environ.get("UMALIB_CFG", "").strip()
    if env:
        cands.append(env)
    cands.append(os.path.join(GAME_DIR, "hachimi", "umalib.json"))
    cands.append(os.path.join(REPLAY, "umalib.json"))
    # 已存在优先，否则用第一个可写位置
    for c in cands:
        if os.path.isfile(c):
            return c
    return cands[0] if cands else os.path.join(REPLAY, "umalib.json")


UMALIB_CFG = _umalib_cfg_path()

# intercept 不再用文件：统一由 umalib.json 的 offline 字段控制（插件第一优先级）
SWITCHES = {
    "intercept": None,  # 虚拟键，toggle 特判
    "mark": os.path.join(REPLAY, "mark.on"),
    "ksdump": os.path.join(REPLAY, "ksdump.on"),
    "urlpatch_off": os.path.join(REPLAY, "urlpatch.off"),
}
LOG = os.path.join(REPLAY, "localsrv.log")
TOOLS = os.path.dirname(os.path.abspath(__file__))
PYEXE = sys.executable


def _umalib_get(key):
    """读 umalib.json（插件第一优先级配置）。"""
    try:
        with open(UMALIB_CFG, "r", encoding="utf-8") as f:
            return json.load(f).get(key)
    except Exception:
        return None


def _umalib_set(**kw):
    """写 umalib.json，保留其它字段。"""
    d = {}
    try:
        with open(UMALIB_CFG, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.update(kw)
    try:
        with open(UMALIB_CFG, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _replay_stats() -> dict:
    try:
        import struct
        b = open(REPLAY_BIN, "rb").read()
        if b[:4] != b"RPLY":
            return {"count": 0, "size": len(b)}
        n = struct.unpack_from("<I", b, 4)[0]
        off = 8
        entries = []
        for _ in range(n):
            src, decl, dl = struct.unpack_from("<III", b, off)
            off += 12
            off += dl
            entries.append(decl)
        return {"count": n, "size": len(b), "declared": sorted(entries, reverse=True)[:10]}
    except Exception as e:
        return {"count": 0, "size": 0, "error": str(e)}


def _replay_map() -> dict:
    """declared -> data_len"""
    try:
        import struct
        b = open(REPLAY_BIN, "rb").read()
        if b[:4] != b"RPLY":
            return {}
        n = struct.unpack_from("<I", b, 4)[0]
        off = 8
        out = {}
        for _ in range(n):
            src, decl, dl = struct.unpack_from("<III", b, off)
            off += 12
            out[decl] = dl
            off += dl
        return out
    except Exception:
        return {}


def _game_alive() -> bool:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process UmamusumePrettyDerby_Jpn -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=8,
        )
        return out.stdout.strip() not in ("", "0")
    except Exception:
        return False


def _run_tool(script: str) -> dict:
    try:
        p = subprocess.run([PYEXE, os.path.join(TOOLS, script)],
                           capture_output=True, text=True, timeout=180)
        return {"ok": p.returncode == 0, "out": ((p.stdout or "") + (p.stderr or ""))[-800:]}
    except Exception as e:
        return {"ok": False, "out": str(e)}


def _decl_map() -> dict:
    try:
        return json.load(open(DECL_JSON, encoding="utf-8"))
    except Exception:
        return {}


# 走「服务器现场生成」的接口：数据在 dynamic/ 下，不进 replay.bin
DYNAMIC_PATHS = {"gacha/exec"}


def status() -> dict:
    rm = _replay_map()
    dm = _decl_map()
    eps = []
    for path, decl in sorted(dm.items()):
        is_dynamic = path in DYNAMIC_PATHS
        eps.append({
            "path": path,
            "declared": decl,
            # 负数表示「不压缩」，真实键是它的绝对值；
            # 动态接口的数据在 dynamic/ 下，不查 replay.bin
            "ok": True if is_dynamic else ((abs(decl) in rm) if decl != 0 else True),
            "empty": decl == 0,
            "dynamic": is_dynamic,
        })
    return {
        "time": time.strftime("%H:%M:%S"),
        "switches": {
            # intercept 读 umalib.json（插件权威源），并兼容旧的 intercept.on
            "intercept": (_umalib_get("offline") is True)
            or os.path.exists(os.path.join(REPLAY, "intercept.on")),
            "mark": os.path.exists(SWITCHES["mark"]),
            "ksdump": os.path.exists(SWITCHES["ksdump"]),
            "urlpatch_off": os.path.exists(SWITCHES["urlpatch_off"]),
        },
        "replay": {"count": len(rm), "size": os.path.getsize(REPLAY_BIN) if os.path.exists(REPLAY_BIN) else 0},
        "paths": len(dm),
        "game": _game_alive(),
        "endpoints": eps,
    }


def read_log(tail: int = 200) -> list[str]:
    try:
        with open(LOG, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [ln.rstrip("\n") for ln in lines[-tail:]]
    except Exception:
        return []


def _db_path() -> str:
    import os
    return os.path.join(REPLAY, "offline.db")


def _get_mode() -> str:
    """读数据库里的模式：'offline' / 'online'。默认 offline。"""
    try:
        import sqlite3 as _sq
        con = _sq.connect(_db_path(), timeout=3)
        r = con.execute("SELECT value FROM meta WHERE key='mode'").fetchone()
        con.close()
        if r and r[0] in ("offline", "online"):
            return r[0]
    except Exception:
        pass
    return "offline"


def _set_mode(mode: str) -> None:
    try:
        import sqlite3 as _sq
        con = _sq.connect(_db_path(), timeout=5)
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('mode',?)", (mode,))
        con.commit()
        con.close()
    except Exception:
        pass


def _cfg_read(key: str, default: str = "") -> str:
    try:
        import sqlite3 as _sq
        con = _sq.connect(_db_path(), timeout=3)
        r = con.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        con.close()
        if r and r[0] is not None:
            return r[0]
    except Exception:
        pass
    return default


def _cfg_write(key: str, value: str) -> None:
    try:
        import sqlite3 as _sq
        con = _sq.connect(_db_path(), timeout=5)
        con.execute("INSERT OR REPLACE INTO config(key, value, updated_at) "
                    "VALUES (?,?,datetime('now'))", (key, value))
        con.commit()
        con.close()
    except Exception:
        pass


def handle_api(path: str, query: dict) -> tuple[int, str, bytes]:
    """返回 (status, content_type, body)。"""
    # 配置读写：/api/config            → 返回全部
    #           /api/config?key=X      → 返回单个
    #           /api/config?key=X&value=Y → 写入
    if path == "/api/config":
        key = (query.get("key") or [""])[0]
        val = (query.get("value") or [None])[0]
        if key and val is not None:
            _cfg_write(key, val)
            return 200, "application/json", json.dumps(
                {"key": key, "value": val}, ensure_ascii=False).encode()
        if key:
            return 200, "text/plain", _cfg_read(key).encode()
        try:
            import sqlite3 as _sq
            con = _sq.connect(_db_path(), timeout=3)
            d = dict(con.execute("SELECT key, value FROM config").fetchall())
            con.close()
        except Exception:
            d = {}
        return 200, "application/json", json.dumps(d, ensure_ascii=False).encode()

    # 一次拿全部开关（插件用）：offline / ctrdump / mark / ksdump / urlpatch_off
    if path == "/api/switches":
        d = {
            "offline": _get_mode() == "offline",
            "ctrdump": _cfg_read("switch.ctrdump", "0") == "1",
            "mark": _cfg_read("switch.mark", "0") == "1",
            "ksdump": _cfg_read("switch.ksdump", "0") == "1",
            "urlpatch_off": _cfg_read("switch.urlpatch_off", "0") == "1",
        }
        return 200, "application/json", json.dumps(d, separators=(",", ":")).encode()

    # 插件启动时探测：1=离线（拦截+URL 指向本地），0=在线（走真服务器）
    if path == "/api/offline":
        v = b"1" if _get_mode() == "offline" else b"0"
        return 200, "text/plain", v

    if path == "/api/status":
        return 200, "application/json", json.dumps(status(), ensure_ascii=False).encode()

    if path == "/api/log":
        return 200, "application/json", json.dumps({"lines": read_log()}, ensure_ascii=False).encode()

    if path == "/api/toggle":
        name = (query.get("name") or [""])[0]
        if name not in SWITCHES:
            return 400, "application/json", b'{"error":"unknown switch"}'
        if name == "intercept":
            # 统一开关：写 umalib.json（插件读它），并同步旧文件哨兵
            cur = _umalib_get("offline")
            if cur is None:
                cur = os.path.exists(os.path.join(REPLAY, "intercept.on"))
            _umalib_set(offline=not cur)
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
            # 状态同时写入 DB config.switch.<name> 和文件哨兵（插件兼容）
            cur = _cfg_read(f"switch.{name}", "0") == "1"
            _cfg_write(f"switch.{name}", "0" if cur else "1")
            p = SWITCHES[name]
            if p:
                if os.path.exists(p):
                    os.remove(p)
                else:
                    open(p, "w").close()
        return 200, "application/json", json.dumps(status(), ensure_ascii=False).encode()

    if path == "/api/mode":
        """mode=online → 在线录制（走真服务器，不拦截，不改 URL）
        mode=local  → 离线回放（拦截 + URL 指向本地）
        """
        mode = (query.get("mode") or [""])[0]
        sentinel = os.path.join(REPLAY, "intercept.on")
        urloff = SWITCHES["urlpatch_off"]
        ctr = os.path.join(REPLAY, "ctrdump.on")

        if mode == "online":
            _set_mode("online")
            _umalib_set(offline=False, url="https://api.games.umamusume.jp/umamusume")
            # 不拦截
            if os.path.exists(sentinel):
                os.remove(sentinel)
            # 不改 URL（走真服务器）
            if not os.path.exists(urloff):
                open(urloff, "w").close()
            # 请求明文落盘（录制必需）
            if not os.path.exists(ctr):
                open(ctr, "w").close()
        elif mode == "local":
            _set_mode("offline")
            _umalib_set(offline=True, url="http://127.0.0.1:826/umamusume")
            try:
                open(sentinel, "w").close()
            except Exception:
                pass
            # URL 指向本地
            if os.path.exists(urloff):
                os.remove(urloff)
        else:
            return 400, "application/json", b'{"error":"bad mode"}'
        return 200, "application/json", json.dumps(status(), ensure_ascii=False).encode()

    if path == "/api/rebuild":
        # 增量合并：只添加/更新当前会话抓到的接口，旧条目保留
        r1 = _run_tool("rebuild_merge.py")
        r2 = _run_tool("sync_all_sid.py")
        st = status()
        st["rebuild"] = {"ok": r1["ok"] and r2["ok"], "out": r1["out"] + "\n" + r2["out"]}
        return 200, "application/json", json.dumps(st, ensure_ascii=False).encode()

    if path == "/api/game":
        action = (query.get("action") or [""])[0]
        if action == "start":
            if not _game_alive():
                subprocess.Popen([GAME_EXE], cwd=GAME_DIR, close_fds=True)
            time.sleep(1)
            return 200, "application/json", json.dumps({"alive": _game_alive()}).encode()
        if action == "stop":
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process UmamusumePrettyDerby_Jpn -ErrorAction SilentlyContinue | Stop-Process -Force"],
                capture_output=True, timeout=15,
            )
            time.sleep(1)
            return 200, "application/json", json.dumps({"alive": _game_alive()}).encode()
        return 200, "application/json", json.dumps({"alive": _game_alive()}).encode()

    return 404, "application/json", b'{"error":"not found"}'

