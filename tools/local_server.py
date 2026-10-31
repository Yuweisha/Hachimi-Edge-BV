"""本地响应服务器：配合插件的 URL 重写使用。

游戏被改成请求 http://127.0.0.1:8080/umamusume/<path>
服务器按路径查数据目录下的响应文件，解码后返回二进制。

用法：
    python local_server.py            # 监听 8080
    python local_server.py --port 9000
"""
from __future__ import annotations

import time
from pathlib import Path

import argparse

# ============================================================================
# 会话会话密钥（由插件上报）与统一响应封装
# ============================================================================

# path -> (key: bytes(16), iv16: bytes(16), ts: float)
# 客户端每个请求用独立 IV，所以按接口路径分别保存最近一次。
_SESSION_KEYS = {}
_LAST_KEY = [None, None, 0.0]   # 全局兜底：[key, iv16, ts]


def set_session_key(sid: str, key_hex: str, iv_hex: str, path: str = "") -> bool:
    """登记会话密钥。

    key_hex 32 字符，iv_hex 32 字符（IV12+ctr 共 16 字节），
    path 为接口路径（如 tool/start_session），为空则同时写入全局兜底。
    """
    try:
        key = bytes.fromhex(key_hex)
        iv16 = bytes.fromhex(iv_hex)
    except ValueError:
        return False
    if len(key) != 16 or len(iv16) != 16:
        return False

    entry = (key, iv16, time.time())
    if path:
        _SESSION_KEYS[path.strip("/")] = entry
    _LAST_KEY[0], _LAST_KEY[1], _LAST_KEY[2] = entry
    return True


def get_session_crypto(path: str = ""):
    """按路径取密钥，取不到则回落到最近一次。返回 (key, iv16) 或 (None, None)。"""
    if path:
        k = path.strip("/")
        if k in _SESSION_KEYS:
            key, iv16, _ = _SESSION_KEYS[k]
            return key, iv16
    if _LAST_KEY[0] is not None:
        return _LAST_KEY[0], _LAST_KEY[1]
    return None, None


def pack_resp(declared: int, plain: bytes, path: str = "") -> bytes:
    """统一响应封装。

    有会话密钥 → 真加密（客户端原生解密路径可解）
    无会话密钥 → 明文注入（需插件 hook 解密函数，兼容旧流程）
    """
    key, iv16 = get_session_crypto(path)
    if key is not None and iv16 is not None:
        try:
            from game_crypto import encrypt_body
            return encrypt_body(plain, key, iv16[:12], int.from_bytes(iv16[12:], "big"))
        except Exception as e:
            self_log(f"[crypto] 加密失败，回落明文: {e}")
    return struct.pack("<I", declared) + b"\x00" * 32 + plain


def self_log(msg):
    try:
        print(msg, flush=True)
    except Exception:
        pass


import base64
import struct
import http.server
import os
import sys
import urllib.parse

PREFIX = "/umamusume/"
REAL_BASE = "https://api.games.umamusume.jp/umamusume/"

# 线上侦察落盘目录
PROXY_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "proxied")


def _proxy_to_real(handler, rel: str, body: bytes) -> bool:
    """把 rel 原样转发到真服务器，原样写回响应。

    返回 True 表示已处理（调用方应直接 return）。
    开关：meta.proxy_paths，逗号分隔的路径列表，如 "tool/start_session"。
    """
    import urllib.request as _ur

    wanted_raw = _cfg_get("meta.proxy_paths", "")
    if not wanted_raw:
        return False

    wanted = [p.strip().strip("/") for p in wanted_raw.split(",") if p.strip()]
    if rel not in wanted:
        return False

    url = REAL_BASE + rel
    req = _ur.Request(url, data=body if handler.command != "GET" else None, method=handler.command)
    # 转发关键 header（SID 是鉴权，Content-Type 是 msgpack）
    for h in ("SID", "Content-Type", "Accept", "User-Agent", "Accept-Encoding", "X-Request-Id"):
        v = handler.headers.get(h)
        if v:
            req.add_header(h, v)

    try:
        with _ur.urlopen(req, timeout=30) as r:
            data = r.read()
            code = r.status
            ctype = r.headers.get("Content-Type", "application/x-msgpack; charset=utf-8")
    except Exception as e:
        handler.log_message("[proxy] %s 失败: %s", rel, e)
        handler.send_response(502)
        handler.send_header("Content-Length", "0")
        handler.end_headers()
        return True

    # 原样落盘，用于分析密钥材料
    try:
        os.makedirs(PROXY_OUT, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe = rel.replace("/", "_")
        with open(os.path.join(PROXY_OUT, f"{stamp}_{safe}_resp.bin"), "wb") as f:
            f.write(data)
        with open(os.path.join(PROXY_OUT, f"{stamp}_{safe}_req.bin"), "wb") as f:
            f.write(body)
    except Exception:
        pass

    handler.log_message("[proxy] %s -> %d, %d B", rel, code, len(data))
    handler.send_response(code)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    if handler.command != "HEAD":
        handler.wfile.write(data)
    return True


# 数据目录：环境变量 > exe 同目录 > 源码目录 > 开发机兜底
def _resolve_base() -> str:
    import sys as _sys

    # 0) 显式指定（最高优先级）
    env = os.environ.get("UMA_DATA_DIR", "").strip()
    if env and os.path.isdir(env):
        return env

    candidates = []
    # 1) exe 自身所在目录
    #    Nuitka onefile：sys.executable 是 exe，
    #    但 sys.argv[0] / __compiled__ 的 onefile 模式下更可靠的是 os.path.dirname(sys.argv[0])
    for src in (getattr(_sys, "executable", ""), getattr(_sys, "argv", [""])[0] if getattr(_sys, "argv", None) else ""):
        if src:
            d = os.path.dirname(os.path.abspath(src))
            if d and d not in candidates:
                candidates.append(d)
    # 2) 源码模式：本文件所在目录 / tools 的上一级
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(here)
        candidates.append(os.path.join(os.path.dirname(here), "uma_replay"))
    except NameError:
        pass

    if os.environ.get("UMA_DEBUG_BASE"):
        print(f"[base] sys.executable = {getattr(_sys, 'executable', None)}")
        print(f"[base] sys.argv[0]    = {(_sys.argv or [None])[0]}")
        print(f"[base] __file__       = {globals().get('__file__')}")
        for c in candidates:
            print(f"[base] 候选 {c}: replay.bin={os.path.exists(os.path.join(c or '.', 'replay.bin'))}")

    # 谁目录下有 offline.db / replay.bin / path_declared.json 就用谁
    for c in candidates:
        if not c:
            continue
        if (os.path.exists(os.path.join(c, "offline.db"))
                or os.path.exists(os.path.join(c, "replay.bin"))
                or os.path.exists(os.path.join(c, "path_declared.json"))):
            return c

    # 兜底：开发机固定路径（会打印警告）
    return r"C:/Users/Schwarz/uma_replay"


BASE_DIR = _resolve_base()

# 外部剧本（--scenario 指定），非空时覆盖 race_start 的 race_scenario
EXTERNAL_SCENARIO = [None]
DB = BASE_DIR

# 同目录 import（打包成 exe 后也能用）
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from admin_ui import handle_api  # noqa: E402

# 兜底：找不到时返回的最小合法响应（response_code=218 + 空 headers）
FALLBACK = bytes.fromhex("82ad726573706f6e73655f636f6465ccdaac646174615f6865616465727380")


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "/api/" in msg:
            return
        sys.stderr.write("[srv] %s\n" % msg)

    def handle(self):
        # 客户端（游戏/浏览器）用完会主动断开 keep-alive 连接，
        # BaseHTTPRequestHandler 会抛 ConnectionResetError 并打印 traceback。
        # 这是正常行为，静默掉。
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def _serve(self):
        _check_db_mtime(self.server)
        # 请求审计：把路径追加到 requests.log（不随重启清空）
        try:
            import re as _re_audit
            _m_audit = _re_audit.search(r"/umamusume/+(.+?)(?:\?|$)", self.path)
            if _m_audit:
                _rel_audit = _m_audit.group(1).rstrip("/")
                _aud = os.path.join(BASE_DIR, "requests.log")
                with open(_aud, "a", encoding="utf-8") as _fa:
                    _fa.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{_rel_audit}\n")
        except Exception:
            pass
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n) if n else b""

        # ===== 请求解密：把客户端发来的密文还原成 msgpack =====
        # 仅对业务路径（/umamusume/*）解密；/api/* 是我们自己的明文接口。
        self.parsed_request = None
        if n and "/umamusume" in self.path:
            # 取接口路径，用于按 path 查 key
            _rel_for_key = self.path
            if "/umamusume" in _rel_for_key:
                _rel_for_key = _rel_for_key.split("/umamusume", 1)[1].strip("/").split("?")[0]

            # 插件是在请求加密阶段上报 key 的，可能晚于本请求到达。
            # 最多等 600ms，每轮换最新 key 重试。
            _pr = None
            for _attempt in range(6):
                _key, _iv16 = get_session_crypto(_rel_for_key)
                if _key is None:
                    time.sleep(0.1)
                    continue
                try:
                    from game_crypto import parse_request, summarize_request
                    _pr = parse_request(body, _key, _iv16)
                    if _pr.get("ok"):
                        print(f"[req] {_rel_for_key} → {summarize_request(_pr)}", flush=True)
                        break
                    # 解密失败：可能是 key/iv 不匹配，等一下再试最新的一组
                    time.sleep(0.1)
                except Exception as _e:
                    print(f"[req] 解密模块异常: {_e}", flush=True)
                    break

            if _pr is None:
                print(f"[req] {_rel_for_key} → 无可用会话密钥", flush=True)
            elif not _pr.get("ok"):
                # dump 现场，便于离线复现
                import os as _os_d
                _dd = _os_d.path.join(BASE_DIR, "reqdump")
                _os_d.makedirs(_dd, exist_ok=True)
                _stamp = time.strftime("%H%M%S") + f"_{len(_dd)}"
                _k, _iv = get_session_crypto(_rel_for_key)
                try:
                    with open(_os_d.path.join(_dd, f"{_stamp}.meta"), "w", encoding="utf-8") as _f:
                        _f.write(f"path={_rel_for_key}\n")
                        _f.write(f"body_len={len(body)}\n")
                        _f.write(f"key={_k.hex().upper() if _k else ''}\n")
                        _f.write(f"iv={_iv.hex().upper() if _iv else ''}\n")
                        _f.write(f"error={_pr.get('error')}\n")
                        _f.write(f"raw_dec={_pr.get('raw_dec')}\n")
                        _f.write(f"lz4_ok={_pr.get('lz4_ok')}\n")
                    with open(_os_d.path.join(_dd, f"{_stamp}.body"), "wb") as _f:
                        _f.write(body)
                    with open(_os_d.path.join(_dd, f"{_stamp}.plain"), "wb") as _f:
                        _f.write(_pr.get("plain") or b"")
                    print(f"[req] {_rel_for_key} → {_pr.get('error')}（已 dump 到 reqdump/{_stamp}）", flush=True)
                except Exception as _de:
                    print(f"[req] {_rel_for_key} → {_pr.get('error')}（dump 失败 {_de}）", flush=True)
            self.parsed_request = _pr

        # ===== 线探针：记录请求头 SID 与密文头部 =====
        # 目的：验证 (1) 密文开头 4 字节的含义 (2) sid16/udid16 的位置
        #       (3) key = MD5(sid16 ‖ HDR[32:52]) 这条公式是否成立
        # 只在 umamusume 路径上启用，写到 uma_replay/reqwire/
        try:
            if n and "/umamusume" in self.path:
                import os as _os, time as _t, re as _re_w
                _m = _re_w.search(r"/umamusume/+(.+?)(?:\?|$)", self.path)
                _relw = _m.group(1).rstrip("/") if _m else "?"
                _dirw = _os.path.join(BASE_DIR, "reqwire")
                _os.makedirs(_dirw, exist_ok=True)
                _sid = self.headers.get("SID", "") or ""
                _udid_hdr = self.headers.get("UDID", "") or ""
                _namew = "%s_%s.txt" % (_t.strftime("%H%M%S"), _relw.replace("/", "#"))
                with open(_os.path.join(_dirw, _namew), "w", encoding="utf-8") as _fw:
                    _fw.write("path = %s\n" % _relw)
                    _fw.write("len  = %d\n" % n)
                    _fw.write("SID  = %s\n" % _sid)
                    _fw.write("SID_len = %d\n" % len(_sid))
                    for _h in ("X-Request-Id", "User-Agent", "Content-Type"):
                        _v = self.headers.get(_h, "")
                        if _v:
                            _fw.write("%s = %s\n" % (_h, _v[:80]))
                    _fw.write("\nhead96 =\n")
                    _hex = body[:96].hex()
                    for _i in range(0, len(_hex), 32):
                        _fw.write("  %04X: %s\n" % (_i // 2, _hex[_i:_i+32].upper()))
        except Exception:
            pass

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        # ===== 插件控制接口（必须放在 /api/ 通用分发之前）=====
        # GET  /api/offline       -> "1" 服务器在跑，插件应切离线模式
        # POST /api/session_key   -> 插件上报 (sid, key, iv)，供响应加密
        if path == "/api/offline":
            # ★ 跟随 meta.mode：online 时返回 "0"，插件才不会改写 URL
            try:
                _rb = b"0" if not _srv_is_offline() else b"1"
            except Exception:
                _rb = b"1"
            print(f"[api/offline] -> {_rb.decode()}", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(_rb)))
            self.end_headers()
            self.wfile.write(_rb)
            return

        if path == "/api/session_key":
            _rb = b"0"
            try:
                import json as _json_sk
                _txt = body.decode("utf-8", errors="replace") if body else "{}"
                _d = _json_sk.loads(_txt)
                _sid = str(_d.get("sid") or "default")
                _k = str(_d.get("key") or "")
                _iv = str(_d.get("iv") or "")
                if set_session_key(_sid, _k, _iv):
                    _rb = b"1"
                    print(f"[crypto] 登记会话密钥 sid={_sid[:16]} key={_k[:8]}… iv={_iv[:8]}…", flush=True)
                else:
                    print(f"[crypto] 密钥无效 keylen={len(_k)} ivlen={len(_iv)}", flush=True)
            except Exception as _e:
                print(f"[crypto] session_key 失败: {_e}", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(_rb)))
            self.end_headers()
            self.wfile.write(_rb)
            return

        if path.startswith("/api/"):
            code, ctype, body = handle_api(path, query)
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        rel = path[len(PREFIX):] if path.startswith(PREFIX) else path.lstrip("/")
        rel = rel.replace("\x00", "")
        while "//" in rel:
            rel = rel.replace("//", "/")
        rel = rel.strip("/")
        try:
            self.log_message("SERVE rel=%s method=%s", rel, self.command)
        except Exception:
            pass

        # ===== 线上侦察：把指定路径反向代理到真服务器 =====
        # 开关在 meta.proxy_paths（逗号分隔）。命中时原样转发请求、原样返回响应，
        # 用于抓真实加密响应（本地伪造的响应头全 0，看不到密钥材料）。
        _proxied = _proxy_to_real(self, rel, body)
        if _proxied:
            return

        # ===== 托管育成（idle_single_mode）—— 服务器权威随机生成 =====
        # 优先用数据库里的真数据（抓包导入的）；没有才动态生成。
        if rel.startswith("idle_single_mode/") and rel in _db_cached_paths():
            # 缓存里的 start_time/end_time 是录制时的，必须改成当前时间，
            # 否则客户端看到倒计时已过、直接判结束。
            try:
                import msgpack as _mp_t
                import base64 as _b64_t
                _row_t = _fetch_cached(rel)
                if _row_t and rel.endswith("/start"):
                    _o = _mp_t.unpackb(_row_t, raw=False, strict_map_key=False)
                    _pi = _o.get("data", {}).get("progress_info", {})
                    if isinstance(_pi, dict):
                        _now = int(time.time())
                        _dur = int(_cfg_get("idle_duration", "60"))
                        _pi["start_time"] = _now
                        _pi["end_time"] = _now + _dur
                        _h = _o.setdefault("data_headers", {})
                        _h["servertime"] = _now
                        _cs = session_sid()
                        if _cs:
                            _h["sid"] = _cs
                    _pl = _mp_t.packb(_o, use_bin_type=True)
                    _bd = _b64_t.b64encode(pack_resp(len(_pl), _pl, rel))
                    print(f"[idle] {rel} -> 缓存+刷新时间 {_pl and len(_pl)} B 明文", flush=True)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-msgpack")
                    self.send_header("Content-Length", str(len(_bd)))
                    self.end_headers()
                    self.wfile.write(_bd)
                    return
            except Exception as _e_t:
                print(f"[idle] 缓存刷新失败: {_e_t}", flush=True)
            # 其它 idle 接口走正常缓存分支
        elif rel.startswith("idle_single_mode/"):
            try:
                import idle_single as _idle
                _act = rel.split("/", 1)[1]
                if _act == "pre_start":
                    _obj = _idle.build_pre_start()
                elif _act == "start":
                    _obj = _idle.build_start()
                elif _act == "end":
                    _obj = _idle.build_end()
                elif _act == "check_progress_log":
                    # 进度日志：空结构即可，客户端只用来渲染列表
                    _obj = {
                        "data_headers": {"result_code": 1, "servertime": int(time.time())},
                        "data": {"progress_log_array": []},
                        "response_code": 1,
                    }
                else:
                    _obj = None

                if _obj is not None:
                    # data_headers 的 sid / servertime 是否替换，可用环境变量切换
                    #   UMACAP_IDLE_RAW=1 → 原样返回录制值（排查用）
                    import os as _os_i
                    if _os_i.environ.get("UMACAP_IDLE_RAW") != "1":
                        try:
                            _h = _obj.get("data_headers")
                            if isinstance(_h, dict):
                                _cur_sid = session_sid()
                                if _cur_sid:
                                    _h["sid"] = _cur_sid
                                _h["servertime"] = int(time.time())
                        except Exception as _e_h:
                            print(f"[idle] header 替换失败: {_e_h}", flush=True)

                    import msgpack as _mp_i
                    import base64 as _b64_i
                    _plain = _mp_i.packb(_obj, use_bin_type=True)
                    # ★ 必须 base64：客户端按 base64 文本解析，裸 pack_resp 字节会直接失败
                    _body = _b64_i.b64encode(pack_resp(len(_plain), _plain, rel))
                    print(f"[idle] {_act} -> {len(_plain)} B 明文, {len(_body)} B base64", flush=True)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-msgpack")
                    self.send_header("Content-Length", str(len(_body)))
                    self.end_headers()
                    self.wfile.write(_body)
                    return
            except Exception as _e:
                print(f"[idle] {rel} 生成失败: {_e}", flush=True)

        # ===== 动态数据拉取（插件用）=====
        # GET /umamusume/dynamic/<n>  -> dynamic/<n>.msgpack 原始字节
        if rel.startswith("dynamic/"):
            name = rel[len("dynamic/"):].strip("/")
            if name.isdigit() and name:
                import os as _os4
                p = _os4.path.join(DYNAMIC_DIR, f"{name}.msgpack")
                if _os4.path.exists(p):
                    data = open(p, "rb").read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    if self.command != "HEAD":
                        self.wfile.write(data)
                    self.log_message("dynamic %s -> %d B", name, len(data))
                    return
                else:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    self.log_message("dynamic %s -> 404", name)
                    return

        seq = 0
        # 在线模式：转发到官方；离线模式：回放本地数据
        _online = (not _srv_is_offline()) or bool(getattr(self.server, "proxy", False))
        if _online:
            # 转发到真实服务器，记录路径 -> src[0:4]
            upstream = "https://api.games.umamusume.jp/umamusume/" + rel
            try:
                import urllib.request as _ur
                req = _ur.Request(upstream, data=body, method=self.command)
                for k, v in self.headers.items():
                    if k.lower() in ("host", "content-length", "connection", "accept-encoding"):
                        continue
                    req.add_header(k, v)
                with _ur.urlopen(req, timeout=30) as r:
                    data = r.read()
            except Exception as e:
                self.log_message("proxy FAIL %s: %s", rel, e)
                data = b""
            # 落盘请求体（诊断用，便于分析入参格式）
            try:
                import os as _os2
                rd = os.path.join(BASE_DIR, "req")
                _os2.makedirs(rd, exist_ok=True)
                rsafe = rel.replace("/", "_")
                with open(f"{rd}/{rsafe}.req", "wb") as _f:
                    _f.write(body)
            except Exception:
                pass

            import base64 as _b64
            # 落盘原始响应（诊断用）
            try:
                import os as _os
                dd = os.path.join(BASE_DIR, "raw")
                _os.makedirs(dd, exist_ok=True)
                safe = rel.replace("/", "_")
                open(f"{dd}/{safe}.raw", "wb").write(data)
                self.log_message("raw saved: %s (%d B)", safe, len(data))
            except Exception:
                pass
            try:
                raw = _b64.b64decode(data)
                if len(raw) >= 4:
                    decl = struct.unpack_from("<I", raw, 0)[0]
                    if decl == 0 and len(raw) > 36:
                        # IsCompressed=false：明文长度 = 总长 - 36
                        # 用负数编码，回放时据此返回等长假体
                        decl = -(len(raw) - 36)
                    if rel in getattr(self.server, "locked_paths", set()):
                        self.log_message("proxy %s -> declared=%d (锁定，不覆盖)", rel, decl)
                    else:
                        self.server.path_declared[rel] = decl
                    if rel not in getattr(self.server, "locked_paths", set()):
                        # 实时落盘：力杀进程也不会丢
                        try:
                            _json.dump(self.server.path_declared,
                                       open(os.path.join(BASE_DIR, "path_declared.json"), "w"),
                                       indent=2, ensure_ascii=False)
                        except Exception:
                            pass
                else:
                    self.log_message("proxy %s -> 响应太短 raw=%d body=%r", rel, len(raw), data[:80])
            except Exception as e:
                self.log_message("proxy %s -> base64 失败: %s body=%r", rel, e, data[:80])
        else:
            # 回放模式也落盘请求（分析用）
            try:
                import os as _os3
                rd2 = os.path.join(BASE_DIR, "req")
                _os3.makedirs(rd2, exist_ok=True)
                with open(f"{rd2}/replay_{rel.replace('/', '_')}.req", "wb") as _f2:
                    _f2.write(body)
            except Exception:
                pass

            # ① 优先从数据库 response_cache 取（动态渲染接口除外）
            _DYN = {"load/index", "note/index", "gacha/index", "gacha/exec", "gacha/get_history",
        "live_theater_performers_preset/index", "transfer/rotation_exec_multi",
        "circle_chat/polling", "live_theater/index",
                    "note/use_gallery_key", "event_id_chara_id",
                    "card/get_release_card_array", "item_info_array_number",
                    "const_walking/index", "item/show_exchange",
                    "note/save_chara_data", "user/change_favorite_character",
                    "mission/receive", "item/exchange",
                    "tool/get_pre_download_resource_version",
                    "trained_chara/load",
                    "ultimate_race/race_entry",
                    "ultimate_race/race_start",
                    "ultimate_race/reflect_item_effect",
                    "practice_race/race_start"}
            # 社团聊天发表情：专用分支（必须在通用回放之前）
            if rel == "circle_chat/send_stamp":
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_render as _dr_cs
                    importlib.reload(_dr_cs)
                    _tpl_cs = _db_template(rel)
                    if _tpl_cs:
                        _req_cs = _latest_req_with("stamp_id")
                        payload_cs = _dr_cs.render_send_stamp(_tpl_cs, _req_cs)
                        hdrs_cs = payload_cs.get("data_headers")
                        if isinstance(hdrs_cs, dict):
                            hdrs_cs["servertime"] = int(time.time())
                        import msgpack as _mp_cs
                        plain_cs = _mp_cs.packb(payload_cs, use_bin_type=True)
                        dlen_cs = len(plain_cs)
                        try:
                            os.makedirs(DYNAMIC_DIR, exist_ok=True)
                            with open(os.path.join(DYNAMIC_DIR, f"{dlen_cs}.msgpack"), "wb") as _f_cs:
                                _f_cs.write(plain_cs)
                        except Exception:
                            pass
                        body_cs = pack_resp(dlen_cs, plain_cs)
                        import base64 as _b64_cs
                        payload_bytes = _b64_cs.b64encode(body_cs)
                        self.log_message("circle_chat/send_stamp -> 动态回显（declared=%d, req=%s）",
                                         dlen_cs, "有" if _req_cs else "无")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(payload_bytes)))
                        self.end_headers()
                        if self.command != "HEAD":
                            self.wfile.write(payload_bytes)
                        return
                except Exception as _e_cs:
                    self.log_message("send_stamp 生成失败: %s", _e_cs)

            if "ultimate_race" in rel:
                self.log_message("[DBG] rel=%r in_DYN=%s", rel, rel in _DYN)
            _cached = None if rel in _DYN else _db_cached(rel)
            # jukebox/index：把录制号主的值换成真实值
            if rel == "jukebox/index" and _cached is not None:
                try:
                    import msgpack as _mp_jb
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import db_render as _dr_jb
                    _cd_jb, _cb_jb = _cached
                    _obj_jb = _mp_jb.unpackb(bytes(_cb_jb), raw=False,
                                             strict_map_key=False, unicode_errors="replace")
                    _obj_jb = _dr_jb.sync_jukebox_index(_obj_jb, 601653962)
                    _nb_jb = _mp_jb.packb(_obj_jb, use_bin_type=True)
                    if _nb_jb != bytes(_cb_jb):
                        _cached = (-len(_nb_jb) if _cd_jb < 0 else len(_nb_jb), _nb_jb)
                except Exception:
                    pass
            if _cached is not None:
                try:
                    import msgpack as _mp_rt
                    _cd, _cb = _cached
                    _obj = _mp_rt.unpackb(bytes(_cb), raw=False,
                                          strict_map_key=False, unicode_errors="replace")
                    _nb, _chg = _refresh_times(rel, _obj)
                    if _chg:
                        # 记住原来的符号（负数=不压缩）
                        _cached = (-len(_nb) if _cd < 0 else len(_nb), _nb)
                except Exception:
                    pass
            if _cached is not None:
                _cdecl, _cplain = _cached
                _plen = len(_cplain) if _cdecl < 0 else len(_cplain)
                try:
                    os.makedirs(DYNAMIC_DIR, exist_ok=True)
                    with open(os.path.join(DYNAMIC_DIR, f"{_plen}.msgpack"), "wb") as _f:
                        _f.write(_cplain[:_plen] if _cdecl < 0 else _cplain)
                except Exception as _e:
                    self.log_message("写 dynamic 失败: %s", _e)
                if _cdecl < 0:
                    # 不压缩：客户端 srcSize = 36 + 明文长度
                    _body = pack_resp(0, b"\x00" * _plen)
                else:
                    _body = pack_resp(_plen, _cplain)
                import base64 as _b64_c
                _payload = _b64_c.b64encode(_body)
                self.log_message("replay %s -> 数据库缓存（declared=%d, %d B）",
                                 rel, _cdecl, len(_cplain))
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", str(len(_payload)))
                self.end_headers()
                self.wfile.write(_payload)
                return

            # 回放：按路径查 declared
            decl = self.server.path_declared.get(rel)
            # tool/get_pre_download_resource_version：告诉客户端"无需预下载"
            # 不返回资源版本 → 游戏不会去 CDN 拉数据
            if rel == "tool/get_pre_download_resource_version":
                import msgpack as _mp2
                payload_v = {
                    "response_code": 1,
                    "data_headers": {"result_code": 1},
                    "data": {},
                }
                body_plain = _mp2.packb(payload_v, use_bin_type=True)
                # 构造 [u32 declared][32B key][data]
                declared_len = len(body_plain)
                body = pack_resp(declared_len, body_plain)
                import base64 as _b64b
                payload = _b64b.b64encode(body)
                self.log_message("replay %s -> 本地空响应（不触发下载）", rel)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            # 写操作落库：返回录制响应的同时更新数据库
            _WRITE_HOOKS = {
                "note/save_chara_data": ("apply_save_chara", ("chara_id", "dress_id")),
                "user/change_favorite_character": ("apply_favorite", ("set_position_info",)),
                "mission/receive": ("apply_mission_receive", None),
                "item/exchange": ("apply_exchange", ("exchange_id",)),
                "note/save_voice": ("apply_save_voice", ("chara_id",)),
                "jukebox/exec_like": ("apply_jukebox_like", ("request_id",)),
                "circle_chat/send_stamp": ("render_send_stamp", ("stamp_id",)),
            }
            self.log_message("WRITE_CHECK rel=%s hit=%s", rel, rel in _WRITE_HOOKS)
            if rel in _WRITE_HOOKS:
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_render as _dr_w
                    importlib.reload(_dr_w)
                    fn_name, fields = _WRITE_HOOKS[rel]
                    req = _latest_req_with(*fields) if fields else None
                    self.log_message("WRITE_REQ fn=%s fields=%s req=%s", fn_name, fields,
                                     ("有" if req else "无"))
                    if fn_name in ("apply_save_chara", "apply_favorite",
                                   "apply_mission_receive", "apply_exchange",
                                   "apply_save_voice", "apply_jukebox_like",
                                   "render_send_stamp"):
                        _tpl_w = _db_template(rel)
                        if _tpl_w:
                            payload_v = getattr(_dr_w, fn_name)(_tpl_w, req)
                            hdrs = payload_v.get("data_headers")
                            if isinstance(hdrs, dict):
                                hdrs["servertime"] = int(time.time())
                            import msgpack as _mpw
                            plain = _mpw.packb(payload_v, use_bin_type=True)
                            dlen = len(plain)
                            try:
                                os.makedirs(DYNAMIC_DIR, exist_ok=True)
                                with open(os.path.join(DYNAMIC_DIR, f"{dlen}.msgpack"), "wb") as _f:
                                    _f.write(plain)
                            except Exception as _e:
                                self.log_message("写 dynamic 失败: %s", _e)
                            body = pack_resp(dlen, plain)
                            import base64 as _b64_w
                            payload = _b64_w.b64encode(body)
                            self.log_message("replay %s -> 落库并回放（declared=%d, req=%s）",
                                             rel, dlen, "有" if req else "无")
                            self.send_response(200)
                            self.send_header("Content-Type", "application/x-msgpack")
                            self.send_header("Content-Length", str(len(payload)))
                            self.end_headers()
                            self.wfile.write(payload)
                            return
                except Exception as _e:
                    self.log_message("%s 落库失败: %s（回退 replay）", rel, _e)

            # gacha/index：按 gacha_visible 勾选情况渲染卡池列表
            if rel == "gacha/index":
                tpl = getattr(self.server, "gacha_index_tpl", None)
                if tpl:
                    try:
                        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                        import importlib
                        import db_render as _dr_g
                        importlib.reload(_dr_g)
                        import copy as _copy_g
                        payload_v = _copy_g.deepcopy(tpl)
                        payload_v["data"] = _dr_g.render_gacha_index(tpl.get("data", {}))
                        hdrs = payload_v.get("data_headers")
                        if isinstance(hdrs, dict):
                            hdrs["servertime"] = int(time.time())
                        import msgpack as _mp_g2
                        plain = _mp_g2.packb(payload_v, use_bin_type=True)
                        dlen = len(plain)
                        try:
                            os.makedirs(DYNAMIC_DIR, exist_ok=True)
                            with open(os.path.join(DYNAMIC_DIR, f"{dlen}.msgpack"), "wb") as _f:
                                _f.write(plain)
                        except Exception as _e:
                            self.log_message("写 dynamic 失败: %s", _e)
                        body = pack_resp(dlen, plain)
                        import base64 as _b64_g2
                        payload = _b64_g2.b64encode(body)
                        self.log_message("replay %s -> 数据库渲染（%d 个池, declared=%d）",
                                         rel, len(payload_v["data"].get("gacha_info_list") or []), dlen)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                    except Exception as _e:
                        self.log_message("gacha/index 渲染失败: %s（回退 replay）", _e)

            # 简单派生接口：从数据库/master 生成（模板从 replay.bin 实时读）
            _SIMPLE_DB = {
                "card/get_release_card_array": "render_release_card_array",
                "item_info_array_number": "render_item_info",
                "const_walking/index": "render_walking",
                "item/show_exchange": "render_show_exchange",
                "gacha/get_history": "render_gacha_history",
                "live_theater_performers_preset/index": "render_live_preset",
                "transfer/rotation_exec_multi": "render_transfer_exec",
                "circle_chat/polling": "render_chat_polling",
                "live_theater/index": "render_live_theater",
            }
            if rel in _SIMPLE_DB:
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_render as _dr_s
                    importlib.reload(_dr_s)
                    _tpl_s = _db_template(rel)
                    if _tpl_s:
                        import copy as _copy_s
                        payload_v = _copy_s.deepcopy(_tpl_s)
                        fn = getattr(_dr_s, _SIMPLE_DB[rel], None)
                        if fn:
                            payload_v["data"] = fn(_tpl_s.get("data", {}))
                        hdrs = payload_v.get("data_headers")
                        if isinstance(hdrs, dict):
                            hdrs["servertime"] = int(time.time())
                        import msgpack as _mp_s
                        plain = _mp_s.packb(payload_v, use_bin_type=True)
                        dlen = len(plain)
                        try:
                            os.makedirs(DYNAMIC_DIR, exist_ok=True)
                            with open(os.path.join(DYNAMIC_DIR, f"{dlen}.msgpack"), "wb") as _f:
                                _f.write(plain)
                        except Exception as _e:
                            self.log_message("写 dynamic 失败: %s", _e)
                        body = pack_resp(dlen, plain)
                        import base64 as _b64_s
                        payload = _b64_s.b64encode(body)
                        self.log_message("replay %s -> 数据库渲染（declared=%d）", rel, dlen)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                except Exception as _e:
                    self.log_message("%s 渲染失败: %s（回退 replay）", rel, _e)

            # trained_chara/load：殿堂（名鉴）点开某匹马时请求，回精简版
            if rel == "trained_chara/load":
                try:
                    import sqlite3 as _sq_tl
                    import msgpack as _mp_tl
                    _dbp_tl = os.path.join(BASE_DIR, "offline.db")
                    _con_tl = _sq_tl.connect(f"file:{_dbp_tl}?mode=ro", uri=True, timeout=3)
                    try:
                        _li = _mp_tl.unpackb(_con_tl.execute(
                            "SELECT data FROM response_cache WHERE path='load/index'"
                        ).fetchone()[0], raw=False, strict_map_key=False,
                            unicode_errors="replace")
                        _tc = (_li.get("data") or {}).get("trained_chara") or []
                        _fav = (_li.get("data") or {}).get("trained_chara_favorite_array") or []
                        _hdr = (_li.get("data_headers") or {})
                    finally:
                        _con_tl.close()
                    # 请求里若带 id 就只返回那些；但 race_entry 遗留的 id 会干扰，
                    # 所以只在请求含 trained_chara_id_array / _list 时才筛选
                    _req = _latest_req_with("trained_chara_id_array", "trained_chara_id_list") or {}
                    _want = (_req.get("trained_chara_id_array")
                             or _req.get("trained_chara_id_list") or [])
                    if isinstance(_want, int):
                        _want = [_want]
                    _sel = ([t for t in _tc if t.get("trained_chara_id") in _want]
                            if _want else _tc)
                    _data = {
                        "trained_chara_array": _sel,
                        "trained_chara_favorite_array": _fav,
                        "room_match_entry_chara_id_array": [],
                        "compare_source_array": [],
                    }
                    _hdr = dict(_hdr)
                    _hdr["servertime"] = int(time.time())
                    _obj = {"response_code": 1, "data_headers": _hdr, "data": _data}
                    _plain = _mp_tl.packb(_obj, use_bin_type=True)
                    _dl = len(_plain)
                    os.makedirs(DYNAMIC_DIR, exist_ok=True)
                    with open(os.path.join(DYNAMIC_DIR, f"{_dl}.msgpack"), "wb") as _f:
                        _f.write(_plain)
                    _body = pack_resp(_dl, _plain)
                    import base64 as _b64_tl
                    _payload = _b64_tl.b64encode(_body)
                    self.log_message("replay %s -> 动态生成（declared=%d, %d 匹）",
                                     rel, _dl, len(_sel))
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-msgpack")
                    self.send_header("Content-Length", str(len(_payload)))
                    self.end_headers()
                    self.wfile.write(_payload)
                    return
                except Exception as _e_tl:
                    self.log_message("%s 生成失败: %s（回退）", rel, _e_tl)

            # ultimate_race/race_entry：按请求里的 trained_chara_id 查库生成
            if rel == "ultimate_race/race_entry":
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_race_entry as _re
                    importlib.reload(_re)

                    # 优先解析当前请求体（格式 base64([u32 len][32B key][msgpack])）。
                    # race_start 不带赛道 ID，只能靠这里记下的上下文；
                    # 从 reqplain 历史文件找会拿到上一局的 ID。
                    _req_cur = {}
                    try:
                        import base64 as _b64e, msgpack as _mpe
                        _raw_e = body
                        try:
                            _raw_e = _b64e.b64decode(body, validate=False)
                        except Exception:
                            pass
                        if len(_raw_e) > 36:
                            _c = _mpe.unpackb(_raw_e[36:], raw=False, strict_map_key=False,
                                              unicode_errors="replace")
                            if isinstance(_c, dict):
                                _req_cur = _c
                    except Exception as _ee:
                        self.log_message("race_entry 请求体解析失败: %s", _ee)

                    # 请求体是加密的，服务器解不出 msgpack；优先读插件落盘的
                    # .req.txt（hook_concat 那里写的明文），最后才退回历史记录。
                    if _req_cur.get("trained_chara_id"):
                        _req = _req_cur
                    else:
                        _req = recent_req_json("ultimate_race/race_entry")
                        if _req:
                            self.log_message(
                                "race_entry 请求体取自插件落盘: trained_chara_id=%s urc=%s",
                                _req.get("trained_chara_id"), _req.get("ultimate_race_id"))
                        else:
                            _req = _latest_req_with("trained_chara_id") or {}
                    _tcid = _req.get("trained_chara_id")

                    import sqlite3 as _sq_re
                    _dbp = os.path.join(BASE_DIR, "offline.db")
                    _con_re = _sq_re.connect(f"file:{_dbp}?mode=ro", uri=True, timeout=3)
                    try:
                        _data, _note = _re.build_race_entry(_con_re, _tcid, _req.get('ultimate_race_id'))
                        _r0 = _con_re.execute(
                            "SELECT data FROM response_cache WHERE path='ultimate_race/race_entry'"
                        ).fetchone()

                        # 记录本局上下文，供 race_start 使用。
                        # nh 必须在这里取 —— 传奇赛按赛事固定 14/17 匹，
                        # race_start 要靠它决定剧本里放几匹马。
                        try:
                            import json as _json_e
                            _nh_now = len((_data or {}).get("race_horse_data_array") or [])
                            _ctx = {
                                "ultimate_race_id": _req.get("ultimate_race_id"),
                                "trained_chara_id": _tcid,
                                "nh": _nh_now,
                                "ts": int(time.time()),
                            }
                            with open(os.path.join(BASE_DIR, "last_race_ctx.json"), "w",
                                      encoding="utf-8") as _fc:
                                _json_e.dump(_ctx, _fc, ensure_ascii=False)
                            self.log_message("race_entry 上下文: urc_id=%s chara=%s nh=%s",
                                             _ctx["ultimate_race_id"], _tcid, _nh_now)
                        except Exception as _ec:
                            self.log_message("写入 race 上下文失败: %s", _ec)
                    finally:
                        _con_re.close()
                    # 【已禁用】按属性预估名次并写 force_rank.txt。
                    # 这条路已经废弃：服务器现在由 gen_race_full 现场生成完整剧本
                    # （Distance + finishTime 都在里面），插件不需要再钉名次。
                    # 而且 rank_from_attrs 用的还是旧的估算公式，写出来的表和
                    # 实际剧本对不上 —— 插件读到它就会把正确结果又覆写掉。
                    # 想恢复就把下面整块取消注释。
                    #
                    # try:
                    #     import rank_from_attrs as _rfa
                    #     importlib.reload(_rfa)
                    #     _urid = (_latest_req_with("ultimate_race_id") or {}).get("ultimate_race_id")
                    #     _dist = _rfa.distance_of(_urid)
                    #     import sqlite3 as _sq_rk
                    #     _con_rk = _sq_rk.connect(f"file:{_dbp}?mode=ro", uri=True, timeout=3)
                    #     try:
                    #         _rnote = _rfa.compute_and_write(_con_rk, _dist)
                    #     finally:
                    #         _con_rk.close()
                    #     self.log_message("race_entry 名次预估: %s", _rnote)
                    # except Exception as _e_rk:
                    #     self.log_message("名次预估失败: %s", _e_rk)

                    if _data is not None and _r0:
                        import msgpack as _mp_re
                        _obj_re = _mp_re.unpackb(_r0[0], raw=False,
                                                 strict_map_key=False, unicode_errors="replace")
                        _obj_re["data"] = _data
                        _hd = _obj_re.get("data_headers")
                        if isinstance(_hd, dict):
                            _hd["servertime"] = int(time.time())
                            _sid_re = session_sid()
                            if _sid_re:
                                _hd["sid"] = _sid_re
                        _plain_re = _mp_re.packb(_obj_re, use_bin_type=True)
                        _dlen = len(_plain_re)
                        os.makedirs(DYNAMIC_DIR, exist_ok=True)
                        with open(os.path.join(DYNAMIC_DIR, f"{_dlen}.msgpack"), "wb") as _f:
                            _f.write(_plain_re)
                        _body = pack_resp(_dlen, _plain_re)
                        import base64 as _b64_re
                        _payload = _b64_re.b64encode(_body)
                        self.log_message("replay %s -> 动态生成（declared=%d）%s",
                                         rel, _dlen, _note)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(_payload)))
                        self.end_headers()
                        self.wfile.write(_payload)
                        return
                except Exception as _e_re:
                    self.log_message("%s 动态生成失败: %s（回退缓存）", rel, _e_re)

            # ultimate_race/race_start：按 trained_chara_id 的属性现场算剧本
            if rel == "ultimate_race/race_start":
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_race_start as _rs
                    importlib.reload(_rs)
                    # 优先解析【当前请求体】：格式 base64([u32 len][32B key][msgpack])
                    # 插件会另外存一份到 reqplain，但那是异步的，且脚本测试根本不会写，
                    # 只靠它会导致 running_style 取到上一局的值甚至取不到。
                    _req_body_s = {}
                    try:
                        import base64 as _b64_s, msgpack as _mp_rb
                        _raw_s = body
                        try:
                            _raw_s = _b64_s.b64decode(body, validate=False)
                        except Exception:
                            pass
                        if len(_raw_s) > 36:
                            _decl_s = struct.unpack_from("<I", _raw_s, 0)[0]
                            _cand = _mp_rb.unpackb(_raw_s[36:], raw=False,
                                                   strict_map_key=False,
                                                   unicode_errors="replace")
                            if isinstance(_cand, dict):
                                _req_body_s = _cand
                    except Exception as _e_rb:
                        self.log_message("race_start 请求体解析失败: %s", _e_rb)

                    # 请求体是加密的；优先读插件落盘的 .req.txt（hook_concat 写的明文）
                    _recent_s = recent_req_json("ultimate_race/race_start")
                    if _recent_s:
                        self.log_message("race_start 请求体取自插件落盘: style=%s",
                                         _recent_s.get("running_style"))
                    _req_s = _recent_s or (_latest_req_with("trained_chara_id") or {})
                    _tcid_s = _req_s.get("trained_chara_id")
                    # running_style：当前请求体优先，其次插件落盘，最后历史记录
                    _reqstyle = _req_body_s.get("running_style")
                    if _reqstyle is None:
                        _reqstyle = _recent_s.get("running_style")
                    if _reqstyle is None:
                        _reqstyle = (_latest_req_with("running_style") or {}).get("running_style")
                    self.log_message("race_start 解析: 当前体=%s style=%s", 
                                     "有" if _req_body_s else "无", _reqstyle)
                    import sqlite3 as _sq_rs
                    _dbp_rs = os.path.join(BASE_DIR, "offline.db")
                    _con_rs = _sq_rs.connect(f"file:{_dbp_rs}?mode=ro", uri=True, timeout=3)
                    try:
                        _scen, _note_s = _rs.build_race_start(_con_rs, _tcid_s, _reqstyle)
                    finally:
                        _con_rs.close()
                    self.log_message("[dbg] EXTERNAL_SCENARIO[0] = %s",
                                     "None" if EXTERNAL_SCENARIO[0] is None
                                     else f"{len(EXTERNAL_SCENARIO[0])} B")
                    # ★ 外部剧本优先，但必须校验马数
                    #   客户端按 race_entry 的 race_horse_data_array 长度分配名次容器，
                    #   剧本 charaNum 不一致会导致「少第一名」甚至卡标题加载。
                    if EXTERNAL_SCENARIO[0] is not None:
                        _ext_b = EXTERNAL_SCENARIO[0]
                        try:
                            _ext_cn = struct.unpack_from("<I", _ext_b, 12)[0]
                        except Exception:
                            _ext_cn = -1
                        # 从最近一次 race_entry 缓存里取实际马数
                        _want_cn = None
                        try:
                            _con_cnt = _sq_rs.connect(
                                f"file:{os.path.join(BASE_DIR, 'offline.db')}?mode=ro",
                                uri=True, timeout=3)
                            try:
                                _row_cnt = _con_cnt.execute(
                                    "SELECT data FROM response_cache "
                                    "WHERE path='ultimate_race/race_entry'").fetchone()
                            finally:
                                _con_cnt.close()
                            if _row_cnt:
                                import msgpack as _mpc
                                _objc = _mpc.unpackb(_row_cnt[0], raw=False,
                                                     strict_map_key=False,
                                                     unicode_errors="replace")
                                _arrc = (_objc.get("data") or {}).get("race_horse_data_array") or []
                                if _arrc:
                                    _want_cn = len(_arrc)
                        except Exception as _ec:
                            self.log_message("race_entry 马数读取失败: %s", _ec)

                        if _want_cn is not None and _ext_cn != _want_cn:
                            self.log_message(
                                "外部剧本 charaNum=%d 与实际马数 %d 不符 → 回退动态生成",
                                _ext_cn, _want_cn)
                        else:
                            _scen = _ext_b
                            _note_s = "外部剧本"
                            self.log_message("race_start → 外部剧本 (%d B, %d 马)",
                                             len(_scen), _ext_cn)

                    if _scen:
                        import gzip as _gz, base64 as _b64s, msgpack as _mp_s
                        _r_s = _con_rs_s = None
                        _con_rs2 = _sq_rs.connect(f"file:{_dbp_rs}?mode=ro", uri=True, timeout=3)
                        try:
                            _r_s = _con_rs2.execute(
                                "SELECT data FROM response_cache WHERE path='ultimate_race/race_start'"
                            ).fetchone()
                        finally:
                            _con_rs2.close()
                        _obj_s = _mp_s.unpackb(_r_s[0], raw=False,
                                               strict_map_key=False, unicode_errors="replace")
                        _obj_s["data"]["race_scenario"] = _b64s.b64encode(
                            _gz.compress(_scen, 6)).decode("ascii")
                        # ★ 必须刷新 servertime，否则客户端 DateChange.CheckDateChangeInner
                        #   发现跨天，弹「日期已经变更」并中断流程
                        _hd_s = _obj_s.get("data_headers")
                        if isinstance(_hd_s, dict):
                            _hd_s["servertime"] = int(time.time())
                            _sid_s = session_sid()
                            if _sid_s:
                                _hd_s["sid"] = _sid_s
                        _plain_s = _mp_s.packb(_obj_s, use_bin_type=True)

                        # 段落拼接调试：meta.scenario_override=1 时，
                        # 用 override.msgpack 里的 race_scenario 替换（其余字段保留生成版，
                        # 否则会带上录制时的旧 sid，客户端直接拒绝）
                        try:
                            if _cfg_get("meta.scenario_override", "") == "1":
                                # 放在 dynamic/ 之外：_check_db_mtime 会清空 dynamic/
                                _ovp = os.path.join(BASE_DIR, "override.msgpack")
                                if os.path.exists(_ovp):
                                    with open(_ovp, "rb") as _fov:
                                        _ovraw = _fov.read()
                                    _ovobj = _mp_s.unpackb(_ovraw, raw=False,
                                                           strict_map_key=False)
                                    _ovsc = None
                                    if isinstance(_ovobj, dict):
                                        if "race_scenario" in _ovobj:
                                            _ovsc = _ovobj["race_scenario"]
                                        elif isinstance(_ovobj.get("data"), dict):
                                            _ovsc = _ovobj["data"].get("race_scenario")
                                    if _ovsc:
                                        _obj_s["data"]["race_scenario"] = _ovsc
                                        _plain_s = _mp_s.packb(_obj_s, use_bin_type=True)
                                        self.log_message(
                                            "race_start 用 override 的 race_scenario（%d B）",
                                            len(_plain_s))
                        except Exception as _eov:
                            self.log_message("override 读取失败: %s", _eov)
                        _dlen_s = len(_plain_s)
                        os.makedirs(DYNAMIC_DIR, exist_ok=True)
                        with open(os.path.join(DYNAMIC_DIR, f"{_dlen_s}.msgpack"), "wb") as _f_s:
                            _f_s.write(_plain_s)
                        _body_s = pack_resp(_dlen_s, _plain_s)
                        import base64 as _b64_rs
                        _payload_s = _b64_rs.b64encode(_body_s)
                        self.log_message("replay %s -> 动态生成剧本（declared=%d）%s",
                                         rel, _dlen_s, _note_s)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(_payload_s)))
                        self.end_headers()
                        self.wfile.write(_payload_s)
                        return
                except Exception as _e_rs:
                    self.log_message("%s 剧本生成失败: %s（回退缓存）", rel, _e_rs)

            # ultimate_race/reflect_item_effect：赛前道具生效。
            # 请求 {item_id_array: [...]}，返回应用后的马数据 + 天气/马场。
            # 天气与马场会写进 ctx，供 race_start 调整 t_ref（速度系数）。
            if rel == "ultimate_race/reflect_item_effect":
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_item_effect as _ie
                    importlib.reload(_ie)

                    _req_ie = recent_req_json("ultimate_race/reflect_item_effect")
                    if _req_ie:
                        self.log_message("reflect_item_effect 请求体取自插件落盘: items=%s",
                                         _req_ie.get("item_id_array"))
                    else:
                        _req_ie = {}
                    try:
                        import base64 as _b64i, msgpack as _mpi
                        _raw_i = body
                        try:
                            _raw_i = _b64i.b64decode(body, validate=False)
                        except Exception:
                            pass
                        if len(_raw_i) > 36:
                            _c_i = _mpi.unpackb(_raw_i[36:], raw=False,
                                                strict_map_key=False, unicode_errors="replace")
                            if isinstance(_c_i, dict):
                                _req_ie = _c_i
                    except Exception as _ei:
                        self.log_message("reflect_item_effect 请求体解析失败: %s", _ei)

                    import sqlite3 as _sq_ie
                    _dbp_ie = os.path.join(BASE_DIR, "offline.db")
                    _con_ie = _sq_ie.connect(f"file:{_dbp_ie}?mode=ro", uri=True, timeout=3)
                    try:
                        _data_ie, _note_ie = _ie.apply_reflect_item_effect(_con_ie, _req_ie)
                    finally:
                        _con_ie.close()

                    if _data_ie:
                        # 天气/马场存进 ctx，race_start 用它调 t_ref
                        try:
                            import json as _json_i
                            _ctxp = os.path.join(BASE_DIR, "last_race_ctx.json")
                            _ctx0 = {}
                            if os.path.exists(_ctxp):
                                with open(_ctxp, encoding="utf-8") as _fi:
                                    _ctx0 = _json_i.load(_fi)
                            _ctx0["weather"] = _data_ie.get("weather")
                            _ctx0["ground_condition"] = _data_ie.get("ground_condition")
                            _ctx0["ts"] = int(time.time())
                            with open(_ctxp, "w", encoding="utf-8") as _fi:
                                _json_i.dump(_ctx0, _fi, ensure_ascii=False)
                        except Exception as _ec2:
                            self.log_message("ctx 写入天气失败: %s", _ec2)

                        import msgpack as _mp_ie
                        # ★ 必须保留 response_code / data_headers，否则客户端报
                        #   “无法读取服务器数据”。race_entry 那边就是这么做的。
                        _obj_ie = _db_template(rel)
                        if isinstance(_obj_ie, dict):
                            _obj_ie["data"] = _data_ie
                            _hd_ie = _obj_ie.get("data_headers")
                            if isinstance(_hd_ie, dict):
                                _hd_ie["servertime"] = int(time.time())
                                _sid_ie = session_sid()
                                if _sid_ie:
                                    _hd_ie["sid"] = _sid_ie
                        else:
                            _obj_ie = _data_ie
                        _plain_ie = _mp_ie.packb(_obj_ie, use_bin_type=True)
                        _dlen_ie = len(_plain_ie)
                        os.makedirs(DYNAMIC_DIR, exist_ok=True)
                        with open(os.path.join(DYNAMIC_DIR, f"{_dlen_ie}.msgpack"), "wb") as _f_ie:
                            _f_ie.write(_plain_ie)
                        _body_ie = pack_resp(_dlen_ie, _plain_ie)
                        import base64 as _b64_ie
                        _payload_ie = _b64_ie.b64encode(_body_ie)
                        self.log_message("ultimate_race/reflect_item_effect -> 动态生效（declared=%d）%s",
                                         _dlen_ie, _note_ie)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(_payload_ie)))
                        self.end_headers()
                        self.wfile.write(_payload_ie)
                        return
                    self.log_message("reflect_item_effect 生成失败: %s（回退缓存）", _note_ie)
                except Exception as _e_ie:
                    self.log_message("reflect_item_effect 异常: %s（回退缓存）", _e_ie)

            # practice_race/race_start：自由比赛。
            # 与传奇赛不同：请求直接带 race_instance_id / entry_num / 玩家跑法，
            # 剧本放在 data.race_result_info.race_scenario（不是 data.race_scenario），
            # 场上马数也由请求决定（常见 18 匹），所以不走 ctx 那一套。
            if rel == "practice_race/race_start":
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_practice_race as _pr
                    importlib.reload(_pr)

                    _req_pr = {}
                    try:
                        import base64 as _b64p, msgpack as _mpp
                        _raw_p = body
                        try:
                            _raw_p = _b64p.b64decode(body, validate=False)
                        except Exception:
                            pass
                        if len(_raw_p) > 36:
                            _c_p = _mpp.unpackb(_raw_p[36:], raw=False,
                                                strict_map_key=False, unicode_errors="replace")
                            if isinstance(_c_p, dict):
                                _req_pr = _c_p
                    except Exception as _ep:
                        self.log_message("practice race_start 请求体解析失败: %s", _ep)

                    import sqlite3 as _sq_pr
                    _dbp_pr = os.path.join(BASE_DIR, "offline.db")
                    _con_pr = _sq_pr.connect(f"file:{_dbp_pr}?mode=ro", uri=True, timeout=3)
                    try:
                        _data_pr, _note_pr = _pr.build_practice_race_start(_con_pr, _req_pr)
                    finally:
                        _con_pr.close()

                    # ★ 外部剧本优先：直接替换 data 里的 race_scenario
                    if EXTERNAL_SCENARIO[0] is not None:
                        import gzip as _gz_pr, base64 as _b64x_pr
                        if not isinstance(_data_pr, dict):
                            _data_pr = {}
                        _dd_pr = _data_pr.get("data")
                        if not isinstance(_dd_pr, dict):
                            _dd_pr = {}
                            _data_pr["data"] = _dd_pr
                        _dd_pr["race_scenario"] = _b64x_pr.b64encode(
                            _gz_pr.compress(EXTERNAL_SCENARIO[0], 6)).decode("ascii")
                        _note_pr = "外部剧本"
                        self.log_message("practice_race/race_start → 外部剧本 (%d B)",
                                         len(EXTERNAL_SCENARIO[0]))

                    if _data_pr:
                        import msgpack as _mp_pr
                        _plain_pr = _mp_pr.packb(_data_pr, use_bin_type=True)
                        _dlen_pr = len(_plain_pr)
                        os.makedirs(DYNAMIC_DIR, exist_ok=True)
                        with open(os.path.join(DYNAMIC_DIR, f"{_dlen_pr}.msgpack"), "wb") as _f_pr:
                            _f_pr.write(_plain_pr)
                        _body_pr = pack_resp(_dlen_pr, _plain_pr)
                        import base64 as _b64_pr
                        _payload_pr = _b64_pr.b64encode(_body_pr)
                        self.log_message("practice_race/race_start -> 动态生成（declared=%d）%s",
                                         _dlen_pr, _note_pr)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(_payload_pr)))
                        self.end_headers()
                        self.wfile.write(_payload_pr)
                        return
                    self.log_message("practice_race/race_start 生成失败: %s（回退缓存）", _note_pr)
                except Exception as _e_pr:
                    self.log_message("practice_race/race_start 异常: %s（回退缓存）", _e_pr)

            # load/index 与 note/index：从数据库渲染（chara/card/cloth/event/金币全部来自 offline.db）
            if rel in ("load/index", "note/index"):
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import importlib
                    import db_render as _dr
                    importlib.reload(_dr)
                    tpl = (self.server.load_index_tpl if rel == "load/index"
                           else self.server.note_index_tpl)
                    if tpl:
                        import copy as _copy
                        payload_v = _copy.deepcopy(tpl)
                        if rel == "load/index":
                            payload_v["data"] = _dr.render_load_index(tpl.get("data", {}))
                        else:
                            payload_v["data"] = _dr.render_note_index(tpl.get("data", {}))
                        hdrs = payload_v.get("data_headers")
                        if isinstance(hdrs, dict):
                            hdrs["servertime"] = int(time.time())
                        import msgpack as _mp_li
                        plain = _mp_li.packb(payload_v, use_bin_type=True)
                        dlen = len(plain)
                        try:
                            os.makedirs(DYNAMIC_DIR, exist_ok=True)
                            with open(os.path.join(DYNAMIC_DIR, f"{dlen}.msgpack"), "wb") as _f:
                                _f.write(plain)
                        except Exception as _e:
                            self.log_message("写 dynamic 失败: %s", _e)
                        body = pack_resp(dlen, plain)
                        import base64 as _b64_li
                        payload = _b64_li.b64encode(body)
                        stat = _dr.stats()
                        self.log_message(
                            "replay %s -> 数据库渲染（declared=%d, chara=%d card=%d event=%d）",
                            rel, dlen, stat["owned_chara"], stat["owned_card"],
                            stat["unlocked_event"])
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                    else:
                        self.log_message("%s 模板缺失，回退 replay", rel)
                except Exception as _e:
                    self.log_message("%s 数据库渲染失败: %s（回退 replay）", rel, _e)

            # note/use_gallery_key：返回全量事件列表（已全解锁），避免用钥匙后列表被削
            if rel == "note/use_gallery_key":
                import msgpack as _mp_gk
                full_ev = getattr(self.server, "full_event_data", None)
                if full_ev is None:
                    full_ev = []
                payload_v = {
                    "response_code": 1,
                    "data_headers": {"result_code": 1, "servertime": int(time.time())},
                    "data": {
                        "item_info_array": [{"item_id": KEY_ITEM_ID, "number": KEY_COUNT}],
                        "event_data_array": full_ev,
                        "home_story_data_array": [],
                    },
                }
                plain = _mp_gk.packb(payload_v, use_bin_type=True)
                dlen = len(plain)
                try:
                    os.makedirs(DYNAMIC_DIR, exist_ok=True)
                    with open(os.path.join(DYNAMIC_DIR, f"{dlen}.msgpack"), "wb") as _f:
                        _f.write(plain)
                except Exception as _e:
                    self.log_message("写 dynamic 失败: %s", _e)
                body = pack_resp(dlen, plain)
                import base64 as _b64_gk
                payload = _b64_gk.b64encode(body)
                self.log_message("replay %s -> 全量事件（%d 条, declared=%d）",
                                 rel, len(full_ev), dlen)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            # 图鉴剧情回放：按请求里的 story_id 现场生成
            if "event_id_chara_id" in rel or rel.endswith("/play_event"):
                req = _latest_req_story()
                if req and isinstance(req.get("story_id"), int):
                    content = make_event_content(req["story_id"],
                                                 req.get("select_index") or 0)
                    if content:
                        import msgpack as _mp_ev
                        plain = _mp_ev.packb(content, use_bin_type=True)
                        dlen = len(plain)
                        # 关键：把明文写到 dynamic/<declared>.msgpack，
                        # 插件拦截 0x3180 时会按 declared 去读这个文件
                        try:
                            os.makedirs(DYNAMIC_DIR, exist_ok=True)
                            with open(os.path.join(DYNAMIC_DIR, f"{dlen}.msgpack"), "wb") as _f:
                                _f.write(plain)
                        except Exception as _e:
                            self.log_message("写 dynamic 失败: %s", _e)
                        body = pack_resp(dlen, plain)
                        import base64 as _b64_ev
                        payload = _b64_ev.b64encode(body)
                        self.log_message(
                            "replay %s -> 现场生成（story_id=%s, event_id=%s, declared=%d）",
                            rel, req["story_id"], content["data"]["event_id"], dlen)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                self.log_message("replay %s -> 没拿到 story_id，回退", rel)

            # 抽卡：现场生成随机结果，写 dynamic/<declared>.msgpack
            if rel == "gacha/exec" and decl and decl > 0:
                try:
                    base = getattr(self.server, "gacha_base", None)
                    if base:
                        dyn = make_dynamic_gacha(base, decl)
                        if dyn:
                            self.log_message("replay %s -> 现场生成（declared=%d）", rel, decl)
                except Exception as e:
                    self.log_message("replay %s 生成失败: %s", rel, e)
            if decl is None:
                decl = 4116
                self.log_message("replay %s -> UNKNOWN(哨兵 4116)", rel)
            elif decl < 0:
                # IsCompressed=false 的接口（trainer_note / save_voice 等）
                # 客户端会调 0x3180，srcSize = 36 + 明文长度
                plain = -decl
                body = b"\x00\x00\x00\x00" + b"\x00" * 32 + b"\x00" * plain
                self.log_message("replay %s -> UNCOMPRESSED(%d)", rel, plain)
                import base64 as _b64
                payload = _b64.b64encode(body)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)
                return
            elif decl == 0:
                # 真正的空响应
                self.log_message("replay %s -> EMPTY(0)", rel)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            vid = 0
            try:
                vid = int(self.headers.get("ViewerID", "0") or 0)
            except Exception:
                vid = 0
            # 假体缓存：同 (decl, vid) 只构造一次，后续直接复用
            key = (decl, vid)
            data = self.server.fake_cache.get(key)
            if data is None:
                raw = struct.pack("<II", decl, vid) + b"\x00" * 28 + b"\x00" * decl
                import base64 as _b64
                data = _b64.b64encode(raw)
                self.server.fake_cache[key] = data

        self.send_response(200)
        self.send_header("Content-Type", "application/x-msgpack")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(b"%x\r\n" % len(data) + data + b"\r\n")
        self.wfile.write(b"0\r\n\r\n")

    def do_POST(self):
        self._serve()

    def do_GET(self):
        self._serve()




# ---------- 抽卡现场生成 ----------
import sqlite3 as _sqlite3

GACHA_DB = "C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb"
REQPLAIN_DIR = os.path.join(BASE_DIR, "reqplain")
DYNAMIC_DIR = os.path.join(BASE_DIR, "dynamic")
RARITY_W = {3: 0.03, 2: 0.18, 1: 0.79}
_dyn_seq = [0]

# 钥匙道具（note/use_gallery_key 用）
KEY_ITEM_ID = 190
KEY_COUNT = 9999


def _http_dirs() -> list[str]:
    """可能的 hachimi/http 根目录（按优先级）。"""
    out = []
    env = os.environ.get("UMACAP_HTTP_DIR", "").strip()
    if env and os.path.isdir(env):
        out.append(env)
    here = os.path.dirname(os.path.abspath(__file__))
    out.append(os.path.join(os.path.dirname(here), "hachimi", "http"))
    out.append(os.path.join(here, "hachimi", "http"))
    out.append(r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/hachimi/http")
    return out


def recent_req_json(rel: str, max_age: float = 600.0) -> dict:
    """从插件落盘的 {seq}_{path}.req.txt 读最近一次请求明文。

    服务器收到的请求体是加密的（[4B len][32B][密文]），解不出 msgpack；
    插件在 hook_concat 里把明文写成 .req.txt，这里直接读。
    路径编码：'/' → '#'，如 ultimate_race#race_entry.req.txt
    """
    import json as _json
    import glob as _glob

    pat = f"*_{rel.replace('/', '#')}.req.txt"
    cands = []
    for root in _http_dirs():
        if not os.path.isdir(root):
            continue
        cands.extend(_glob.glob(os.path.join(root, "*", pat)))
    if not cands:
        return {}
    try:
        newest = max(cands, key=os.path.getmtime)
    except Exception:
        return {}
    if time.time() - os.path.getmtime(newest) > max_age:
        return {}
    try:
        with open(newest, encoding="utf-8") as f:
            obj = _json.load(f)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {}


def _latest_req_plain():
    """取 reqplain 下最新的、含 gacha_id 的请求明文（别拿到 note/save_voice 之类）。"""
    try:
        import glob as _g
        import msgpack as _mp
        files = sorted(_g.glob(REQPLAIN_DIR + "/req_*.msgpack"),
                       key=os.path.getmtime, reverse=True)
        for f in files[:40]:
            try:
                v = _mp.unpackb(open(f, "rb").read(), raw=False,
                                strict_map_key=False, unicode_errors="replace")
            except Exception:
                continue
            if isinstance(v, dict) and "gacha_id" in v:
                return f
        return None
    except Exception:
        return None


# ===== 图鉴剧情回放（event_id_chara_id）动态生成 =====

def _db_template(rel: str):
    """从 response_cache 取原始模板（未渲染的响应）。"""
    try:
        import sqlite3 as _sq
        import msgpack as _mp
        dbp = os.path.join(BASE_DIR, "offline.db")
        if not os.path.exists(dbp):
            return None
        con = _sq.connect(f"file:{dbp}?mode=ro", uri=True, timeout=3)
        r = con.execute("SELECT declared, data FROM response_cache WHERE path=?",
                        (rel,)).fetchone()
        con.close()
        if r:
            return _mp.unpackb(bytes(r[1]), raw=False, strict_map_key=False,
                               unicode_errors="replace")
    except Exception:
        pass
    return None


_DB_MTIME = 0.0


def _auto_sync_master() -> None:
    """启动时同步 master 到数据库（master.mdb 变化才跑）。"""
    try:
        import sqlite3 as _sq
        import subprocess
        import sys as _sys

        mdb = GACHA_DB
        dbp = os.path.join(BASE_DIR, "offline.db")
        if not (os.path.exists(mdb) and os.path.exists(dbp)):
            return
        cur_m = os.path.getmtime(mdb)

        con = _sq.connect(dbp, timeout=10)
        row = con.execute("SELECT value FROM meta WHERE key='master_mtime'").fetchone()
        old_m = float(row[0]) if row and row[0] else 0.0
        con.close()

        if abs(cur_m - old_m) < 1.0:
            print("[sync] master 未变化，跳过同步", flush=True)
            return

        t0 = time.time()
        print("[sync] master 已更新 -> 开始同步…", flush=True)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "db_sync_incremental.py")
        if not os.path.exists(script):
            print("[sync] 缺 db_sync_incremental.py，跳过", flush=True)
            return
        r = subprocess.run([_sys.executable, script], capture_output=True,
                           text=True, timeout=600)
        out = (r.stdout or "").strip().splitlines()
        for line in out[-8:]:
            print(f"[sync] {line}", flush=True)
        if r.returncode != 0:
            print(f"[sync] 同步失败 rc={r.returncode}: {(r.stderr or '')[-300:]}", flush=True)
            return
        con = _sq.connect(dbp, timeout=10)
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('master_mtime',?)",
                    (str(cur_m),))
        con.commit()
        con.close()
        print(f"[sync] 同步完成，耗时 {time.time()-t0:.1f}s", flush=True)
    except Exception as e:
        print(f"[sync] 自动同步失败: {e}", flush=True)


def _load_templates(srv) -> None:
    """从 response_cache 加载渲染模板（load/index、note/index、gacha/index）。"""
    srv.load_index_tpl = None
    srv.note_index_tpl = None
    srv.gacha_index_tpl = None
    try:
        for _p, _attr, _label in (
            ("load/index", "load_index_tpl", "load/index"),
            ("note/index", "note_index_tpl", "note/index"),
            ("gacha/index", "gacha_index_tpl", "gacha/index"),
        ):
            _v = _db_template(_p)
            if _v:
                setattr(srv, _attr, _v)
                _dd = _v.get("data", {}) if isinstance(_v, dict) else {}
                print(f"[srv] {_label} 模板已加载（{len(_dd)} 个字段）")
            else:
                print(f"[srv] {_label} 模板缺失")
    except Exception as _e:
        print("[srv] 模板加载失败:", _e)


def _check_db_mtime(srv) -> None:
    """数据库变了就清 dynamic/ 并重载模板（热重载）。"""
    global _DB_MTIME
    try:
        # WAL 模式下写数据只更新 -wal，主库 mtime 不变 → 三个文件一起看
        sig = 0.0
        for _n in ("offline.db", "offline.db-wal", "offline.db-shm"):
            _p = os.path.join(BASE_DIR, _n)
            if os.path.exists(_p):
                try:
                    sig += os.path.getmtime(_p) + os.path.getsize(_p) * 1e-9
                except Exception:
                    pass
        if sig == 0.0:
            return
        m = sig
        if m == _DB_MTIME:
            return
        first = (_DB_MTIME == 0.0)
        _DB_MTIME = m
        if first:
            return
        # 清掉动态缓存，强制下次请求重新渲染
        dyn = os.path.join(BASE_DIR, "dynamic")
        n = 0
        if os.path.isdir(dyn):
            for f in os.listdir(dyn):
                if f.endswith(".msgpack"):
                    try:
                        os.remove(os.path.join(dyn, f))
                        n += 1
                    except Exception:
                        pass
        _load_templates(srv)
        print(f"[srv] 数据库已变更 → 清掉 {n} 个 dynamic 文件并重载模板")
    except Exception as _e:
        print("[srv] 热重载失败:", _e)


_SESSION_SID = ""


def session_sid() -> str:
    """当前会话的 sid —— 取自 start_session 模板。

    客户端用 start_session 返回的 sid 当会话令牌，其他响应若带录制时的旧 sid
    会被 CommonProcessOnResponded 判为非法，表现为「无法读取服务器数据」或卡加载。
    """
    global _SESSION_SID
    if _SESSION_SID:
        return _SESSION_SID
    try:
        import sqlite3 as _sq
        import msgpack as _mp
        dbp = os.path.join(BASE_DIR, "offline.db")
        con = _sq.connect(f"file:{dbp}?mode=ro", uri=True, timeout=3)
        r = con.execute(
            "SELECT data FROM response_cache WHERE path='tool/start_session'").fetchone()
        con.close()
        if r:
            obj = _mp.unpackb(bytes(r[0]), raw=False, strict_map_key=False)
            sid = (obj.get("data_headers") or {}).get("sid")
            if sid:
                _SESSION_SID = str(sid)
    except Exception:
        pass
    return _SESSION_SID


def _refresh_times(rel: str, obj) -> tuple[bytes, bool]:
    """刷新响应里的时间字段：servertime / next_random_request_time / *_time。

    返回 (新 blob, 是否改动)。
    """
    if not isinstance(obj, dict):
        return b"", False

    changed = False
    now = int(time.time())
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))

    hdrs = obj.get("data_headers")
    if isinstance(hdrs, dict):
        old = hdrs.get("servertime")
        if old != now:
            hdrs["servertime"] = now
            changed = True
        # ★ sid 必须统一成当前会话的，否则客户端拒绝整个响应
        _sid = session_sid()
        if _sid and hdrs.get("sid") != _sid:
            hdrs["sid"] = _sid
            changed = True

    dd = obj.get("data")
    if isinstance(dd, dict):
        for k in list(dd.keys()):
            v = dd[k]
            # 「下次 X 时间」如果已过期，推到 1 小时后
            if isinstance(v, str) and "next_" in k and k.endswith("_time"):
                try:
                    t = time.mktime(time.strptime(v, "%Y-%m-%d %H:%M:%S"))
                    if t < now:
                        dd[k] = time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(now + 3600))
                        changed = True
                except Exception:
                    pass
        # request_history 里的 request_time 也刷新
        rh = dd.get("request_history")
        if isinstance(rh, dict) and isinstance(rh.get("request_time"), str):
            if rh["request_time"] < now_str:
                rh["request_time"] = now_str
                changed = True

    if not changed:
        return b"", False
    import msgpack as _mp
    return _mp.packb(obj, use_bin_type=True), True


_CACHED_PATHS = [None]


def _key_channel_udp(port: int = 827) -> None:
    """UDP 密钥通道：接收插件上报的 (path, key, iv)。

    报文（一行 JSON，UTF-8）：
        {"path":"tool/start_session","key":"<32 hex>","iv":"<32 hex>"}

    UDP 无连接；丢一两条不影响，服务器永远只用最新一组。
    """
    import json as _json_k
    import socket as _sock_k

    sock = _sock_k.socket(_sock_k.AF_INET, _sock_k.SOCK_DGRAM)
    try:
        sock.setsockopt(_sock_k.SOL_SOCKET, _sock_k.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
    except Exception as e:
        print(f"[keychan] bind 127.0.0.1:{port} 失败: {e}", flush=True)
        return

    print(f"[keychan] UDP 监听 127.0.0.1:{port}", flush=True)
    cnt = 0
    while True:
        try:
            data, _addr = sock.recvfrom(4096)
        except OSError:
            break
        try:
            d = _json_k.loads(data.decode("utf-8", errors="replace"))
            ok = set_session_key(
                "client",
                str(d.get("key") or ""),
                str(d.get("iv") or ""),
                str(d.get("path") or ""),
            )
            if ok:
                cnt += 1
                if cnt <= 20 or cnt % 50 == 0:
                    print(f"[keychan #{cnt}] {d.get('path','')}  "
                          f"key={str(d.get('key',''))[:8]}… "
                          f"iv={str(d.get('iv',''))[:8]}…", flush=True)
            else:
                print(f"[keychan] 报文无效: {data[:80]!r}", flush=True)
        except Exception as e:
            print(f"[keychan] 解析失败: {e}", flush=True)


def _fetch_cached(rel: str):
    """取某个接口缓存的原始字节。"""
    try:
        con = _sqlite3_conn()
        r = con.execute("SELECT data FROM response_cache WHERE path=?", (rel,)).fetchone()
        con.close()
        return r[0] if r else None
    except Exception:
        return None


def _db_cached_paths() -> set:
    """缓存库里有响应数据的接口集合（惰性加载）。"""
    if _CACHED_PATHS[0] is None:
        try:
            con = _sqlite3_conn()
            _CACHED_PATHS[0] = {r[0] for r in con.execute("SELECT path FROM response_cache")}
            con.close()
        except Exception:
            _CACHED_PATHS[0] = set()
    return _CACHED_PATHS[0]


def _srv_is_offline() -> bool:
    """服务器自己的工作模式：读 meta.mode。offline=回放，online=转发。"""
    try:
        con = _sqlite3_conn()
        r = con.execute("SELECT value FROM meta WHERE key='mode'").fetchone()
        con.close()
        if r and r[0] == "online":
            return False
    except Exception:
        pass
    return True


def _cfg_get(key: str, default: str = "") -> str:
    """从 offline.db 的 config 表读配置。"""
    try:
        con = _sqlite3_conn()
        r = con.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        con.close()
        if r and r[0] is not None:
            return r[0]
    except Exception:
        pass
    return default


def _sqlite3_conn():
    import sqlite3 as _sq
    return _sq.connect(os.path.join(BASE_DIR, "offline.db"), timeout=10)


def _db_cached(rel: str):
    """从 offline.db 的 response_cache 取响应。返回 (declared, plain_bytes) 或 None。"""
    try:
        import sqlite3 as _sq
        dbp = os.path.join(BASE_DIR, "offline.db")
        if not os.path.exists(dbp):
            return None
        con = _sq.connect(f"file:{dbp}?mode=ro", uri=True, timeout=3)
        r = con.execute("SELECT declared, data FROM response_cache WHERE path=?",
                        (rel,)).fetchone()
        con.close()
        if r:
            return int(r[0]), bytes(r[1])
    except Exception:
        pass
    return None


def _latest_req_with(*fields):
    """找含指定字段的最新请求明文。"""
    try:
        import glob as _g
        import msgpack as _mp
        files = sorted(_g.glob(REQPLAIN_DIR + "/req_*.msgpack"),
                       key=os.path.getmtime, reverse=True)
        want = set(fields)
        # 放宽到 400 个：race_start 这类低频请求会被大量 load/index 挤到很后面，
        # 只扫最近 40 个会取不到 running_style，导致跑法不生效。
        for f in files[:400]:
            try:
                v = _mp.unpackb(open(f, "rb").read(), raw=False,
                                strict_map_key=False, unicode_errors="replace")
            except Exception:
                continue
            if isinstance(v, dict) and want <= set(v.keys()):
                return v
    except Exception:
        pass
    return None


def _latest_req_story():
    """取 reqplain 下最新的、含 story_id 的请求明文。"""
    try:
        import glob as _g
        import msgpack as _mp
        files = sorted(_g.glob(REQPLAIN_DIR + "/req_*.msgpack"),
                       key=os.path.getmtime, reverse=True)
        for f in files[:30]:
            try:
                v = _mp.unpackb(open(f, "rb").read(), raw=False,
                                strict_map_key=False, unicode_errors="replace")
            except Exception:
                continue
            if isinstance(v, dict) and "story_id" in v:
                return v
        return None
    except Exception:
        return None


def _story_meta(story_id: int):
    """从 master 查 (chara_id, event_category)。"""
    try:
        import sqlite3 as _sq
        con = _sq.connect(GACHA_DB, timeout=5)
        cur = con.cursor()
        cur.execute(
            "SELECT card_chara_id, event_category FROM single_mode_story_data WHERE story_id=?",
            (story_id,),
        )
        row = cur.fetchone()
        con.close()
        if row:
            return int(row[0]), int(row[1])
    except Exception as e:
        print("[srv] 查 story_meta 失败:", e, flush=True)
    return None, None


def make_event_content(story_id: int, select_index: int = 0):
    """按 story_id 生成图鉴回放响应。"""
    chara_id, cat = _story_meta(story_id)
    if chara_id is None:
        return None
    event_id = (cat + 1) * 1000
    return {
        "response_code": 1,
        "data_headers": {
            "result_code": 1,
            "servertime": int(time.time()),
        },
        "data": {
            "event_id": event_id,
            "chara_id": chara_id,
            "story_id": story_id,
            "event_contents_info": {
                "support_card_id": 0,
                "choice_array": [
                    {
                        "select_index_info_array": [
                            {"branch_number": 1, "select_index": 1}
                        ],
                        "receive_item_id": 0,
                        "target_race_id": 0,
                        "gain_select_id_index": 1,
                        "select_icon": 0,
                    }
                ],
                "month": 4,
                "race_id": 0,
            },
        },
    }


def _parse_gacha_req(path):
    """从请求明文里解析 gacha_id / draw_num。"""
    try:
        import msgpack as _mp
        v = _mp.unpackb(open(path, "rb").read(), raw=False, strict_map_key=False,
                        unicode_errors="replace")
    except Exception:
        return None
    # 常见结构：{gacha_id: N, draw_type: 1|2, ...} 或嵌在 data 里
    def walk(o, depth=0):
        if depth > 4:
            return {}
        out = {}
        if isinstance(o, dict):
            for k, val in o.items():
                if k in ("gacha_id", "draw_type", "draw_num", "gacha_draw_type", "count"):
                    if isinstance(val, int):
                        out[k] = val
                elif isinstance(val, (dict, list)):
                    out.update(walk(val, depth + 1))
        elif isinstance(o, list):
            for x in o[:4]:
                out.update(walk(x, depth + 1))
        return out
    return walk(v)


def _gacha_card_type(gacha_id):
    """判断卡池类型（1=角色卡，2=支援卡）。

    优先查 master.gacha_data；查不到则查 gacha_available；最后默认角色卡。
    """
    try:
        con = _sqlite3.connect(GACHA_DB, timeout=5)
        cur = con.cursor()
        cur.execute("SELECT card_type FROM gacha_data WHERE id=?", (gacha_id,))
        r = cur.fetchone()
        if r and r[0] in (1, 2):
            con.close()
            return int(r[0])
        cur.execute("SELECT DISTINCT card_type FROM gacha_available WHERE gacha_id=?",
                    (gacha_id,))
        rows = cur.fetchall()
        con.close()
        if len(rows) == 1 and rows[0][0] in (1, 2):
            return int(rows[0][0])
    except Exception:
        pass
    return 1


def _draw_cards(gacha_id, n):
    """按数据库卡池抽 n 张。返回 [(card_id, card_type, rarity)]。

    用 db_gacha_v2：全量真实卡池 + 权重表（3%/18%/79%），不依赖 gacha_id 是否存在。
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import importlib
        import db_gacha_v2 as dg
        # 每次都重载：改了 db_gacha_v2 不用重启服务器
        importlib.reload(dg)
    except Exception as e:
        print(f"[srv] 导入 db_gacha_v2 失败: {e}", flush=True)
        return []

    ct = _gacha_card_type(gacha_id)
    cards = dg.draw(card_type=ct, n=n, gacha_id=gacha_id)
    if not cards:
        # 指定的池抽不出东西时，回退到全量同类型池
        cards = dg.draw(card_type=ct, n=n, gacha_id=None)
    if cards:
        # 扣宝石（优先免费，不足扣付费）
        try:
            chg = dg.charge_gacha(gacha_id, len(cards))
            if chg["ok"]:
                print(f"[srv] 抽卡扣宝石 {chg['cost']}：fcoin={chg['fcoin']:,} coin={chg['coin']:,}",
                      flush=True)
            else:
                print(f"[srv] 宝石不足（需要 {chg['cost']}，持有 {chg['fcoin']+chg['coin']:,}）",
                      flush=True)
        except Exception as e:
            print(f"[srv] 扣宝石失败: {e}", flush=True)
        # 落库
        try:
            dg.commit_draw(gacha_id, cards)
        except Exception as e:
            print(f"[srv] 抽卡落库失败: {e}", flush=True)
    return cards


def _build_gacha_response(gacha_id, cards, base_resp):
    """基于一份响应骨架填抽卡结果。"""
    import copy as _copy
    v = _copy.deepcopy(base_resp)
    d = v.setdefault("data", {})
    results = []
    add_pieces = {}
    # 碎片数按稀有度（来自 gacha_data 的 additional_piece 配置）
    PIECE_BY_RARITY = {1: 5, 2: 10, 3: 60}
    for cid, ct, rar in cards:
        piece = PIECE_BY_RARITY.get(rar, 5) if ct == 1 else 0
        results.append({
            "card_type": ct,
            "card_id": cid,
            "piece_id": cid if ct == 1 else 0,
            "common_item_category": 0,
            "common_item_id": 0,
            "convert_piece_num": 0,
            "convert_common_item_num": 0,
            "additional_piece_num": piece,
            "new_flag": 0,
            "win_prize": 0,
        })
        if ct == 1 and piece:
            add_pieces[cid] = add_pieces.get(cid, 0) + piece
    d["gacha_result_list"] = results
    rs = d.setdefault("reward_summary_info", {})
    rs["add_piece_list"] = [{"piece_id": k, "piece_num": n} for k, n in add_pieces.items()]
    rs["add_item_list"] = []
    rs["add_card_list"] = []
    # 支援卡必须填 add_support_card_list，否则客户端当空卡处理（会软死）
    support_cards = []
    support_nums = []
    support_lb = []
    seen = {}
    for cid, ct, rar in cards:
        if ct != 2:
            continue
        if cid in seen:
            seen[cid] += 1
            continue
        seen[cid] = 1
        support_cards.append({
            "support_card_id": cid,
            "exp": 0,
            "limit_break_count": 0,
            "favorite_flag": 0,
            "stock": 0,
            "possess_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        support_lb.append({
            "support_card_id": cid,
            "before_limit_break_count": 0,
            "after_limit_break_count": 0,
            "is_send_stock": False,
            "is_send_present": False,
        })
    for cid, n in seen.items():
        support_nums.append({"support_card_id": cid, "number": n, "item_type": 51})
    rs["add_support_card_list"] = support_cards
    rs["add_support_card_num_array"] = support_nums
    rs["add_support_card_limit_break_array"] = support_lb
    d["bonus_item_array"] = []
    d["item_list"] = []
    # servertime 必须是当前时间，否则客户端判定「日期已变更」
    import time as _t
    hdrs = v.get("data_headers")
    if isinstance(hdrs, dict):
        hdrs["servertime"] = int(_t.time())
    # 宝石不能被旧模板的数值覆盖（否则抽一次卡余额就退回 11140）
    if "coin_info" in d and isinstance(d["coin_info"], dict):
        d["coin_info"]["fcoin"] = 100000000
        d["coin_info"]["coin"] = 100000000
    if "limit_item_info" in d:
        d["limit_item_info"]["gacha_id"] = gacha_id
        d["limit_item_info"]["num"] = len(cards)
    # 从数据库同步最新的金币/宝石（扣费后）
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import db_render as _dr
        _coin = int(_dr.get_state("coin", "0"))
        _fcoin = int(_dr.get_state("fcoin", "0"))
        d["coin_info"] = {"coin": _coin, "fcoin": _fcoin}
        _il = d.get("item_list")
        if not isinstance(_il, list):
            _il = []
        _by = {it.get("item_id"): it for it in _il if isinstance(it, dict)}
        _gold = int(_dr.get_state("gold_item", "0"))
        _key = int(_dr.get_state("key_item", "0"))
        if 59 in _by:
            _by[59]["number"] = _gold
        else:
            _il.append({"item_id": 59, "number": _gold})
        if 190 in _by:
            _by[190]["number"] = _key
        else:
            _il.append({"item_id": 190, "number": _key})
        d["item_list"] = _il
    except Exception as _e:
        print(f"[srv] 同步金币失败: {_e}", flush=True)

    return v


def make_dynamic_gacha(base_resp, declared):
    """生成动态抽卡响应，写到 dynamic/<declared>.msgpack，返回 seq。"""
    import msgpack as _mp
    import json as _json

    req_path = _latest_req_plain()
    info = _parse_gacha_req(req_path) if req_path else None
    gacha_id = (info or {}).get("gacha_id", 30476)
    # 请求抓不到 draw_num（加密后长度相同），改读配置
    n = 1
    try:
        cfg = json.loads(Path(os.path.join(BASE_DIR, "gacha.json")).read_text(encoding="utf-8"))
        n = int(cfg.get("draw_count", 10))
    except Exception:
        n = 10   # 默认十连
    if n not in (1, 10):
        n = 10
    # 如果能从请求解析出 draw_num，优先用它
    req_n = (info or {}).get("draw_num")
    if isinstance(req_n, int) and req_n in (1, 10):
        n = req_n

    cards = _draw_cards(gacha_id, n)
    if not cards:
        return None

    resp = _build_gacha_response(gacha_id, cards, base_resp)
    data = _mp.packb(resp, use_bin_type=True)

    # 长度必须 <= declared，客户端 dst_cap 通常是 declared 的 2 倍
    if len(data) > declared:
        print(f"[srv] 抽卡数据 {len(data)} B 超过 declared {declared}，截断失败", flush=True)
        return None

    os.makedirs(DYNAMIC_DIR, exist_ok=True)
    path = f"{DYNAMIC_DIR}/{declared}.msgpack"
    open(path, "wb").write(data)

    stat = {}
    for _, _, r in cards:
        stat[r] = stat.get(r, 0) + 1
    print(f"[srv] 抽卡 gacha_id={gacha_id} n={n} -> {stat} ({len(data)} B -> {path})", flush=True)
    return True


def main():
    global DB, BASE_DIR
    import json

    # 先把 stdout/stderr 重定向到日志文件，这样 Web 界面的 LOG 面板才能读到。
    # 无论用什么方式启动（shell 重定向、后台任务、双击），都有日志。
    try:
        _log_path = os.path.join(BASE_DIR, "localsrv.log")
        os.makedirs(BASE_DIR, exist_ok=True)
        _lf = open(_log_path, "a", encoding="utf-8", buffering=1, errors="replace")
        sys.stdout = _lf
        sys.stderr = _lf
        print(f"\n{'=' * 60}")
        print(f"[srv] 启动 {time.strftime('%Y-%m-%d %H:%M:%S')}  pid={os.getpid()}")
    except Exception as _e:
        print("[srv] 日志重定向失败:", _e, file=sys.__stderr__)

    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=826)
    ap.add_argument("--proxy", action="store_true")
    ap.add_argument("--data-dir", default=None,
                    help="数据目录（含 replay.bin / path_declared.json）；默认自动探测")
    ap.add_argument("--scenario", default=None,
                    help="外部剧本 bin（指定后覆盖 ultimate_race/race_start 的 race_scenario）")
    a = ap.parse_args()

    # 加载外部剧本
    if a.scenario:
        try:
            _sp = os.path.abspath(a.scenario)
            EXTERNAL_SCENARIO[0] = open(_sp, "rb").read()
            print("[srv] 外部剧本: %s (%d B)" % (_sp, len(EXTERNAL_SCENARIO[0])), flush=True)
        except Exception as _e_sc:
            print("[srv] 外部剧本加载失败: %s" % _e_sc, flush=True)

    if a.data_dir:
        d = os.path.abspath(a.data_dir)
        if not os.path.isdir(d):
            print(f"[错误] --data-dir 不是目录: {d}")
            return 1
        BASE_DIR = d
        DB = d

    if not os.path.isfile(os.path.join(DB, "offline.db")):
        print("=" * 56)
        print("[错误] 找不到 offline.db")
        print(f"  当前数据目录: {DB}")
        print()
        print("  请把 offline.db 放到 exe 同一个目录，或用 --data-dir 指定：")
        print(f'    {os.path.basename(sys.executable)} --data-dir "D:\\你的数据目录"')
        print("=" * 56)
        return 1

    # 目录下的子文件夹数（旧的接口目录结构，可能为 0）
    n = len([d for d in os.listdir(DB) if os.path.isdir(os.path.join(DB, d))])
    print(f"[srv] 数据目录: {DB}")
    print(f"录制库 {n} 个接口，监听 http://{a.host}:{a.port}")
    srv = http.server.ThreadingHTTPServer((a.host, a.port), H)
    srv.hdr_logged = False
    # 读 replay.bin：seq -> 明文长度
    srv.declared_by_seq = {}
    try:
        _rb_path = os.path.join(BASE_DIR, "replay.bin")
        if not os.path.exists(_rb_path):
            raise FileNotFoundError("no replay.bin")
        blob = open(_rb_path, "rb").read()
        if blob[:4] == b"RPLY":
            n = struct.unpack_from("<I", blob, 4)[0]
            off = 8
            for _ in range(n):
                sq, decl, dl = struct.unpack_from("<III", blob, off)
                off += 12
                srv.declared_by_seq[sq] = decl
                off += dl
            print("[srv] replay.bin: %d 条" % n)
    except Exception as e:
        print(f"[srv] replay.bin 跳过（{e}），使用数据库")

    # 路径 -> declared 表（已从数据库加载）

    # 抽卡骨架：从 response_cache 的 _gacha_skeleton_ten 读
    srv.gacha_base = None
    try:
        _gb = _db_template("_gacha_skeleton_ten")
        if _gb:
            srv.gacha_base = _gb
            print("[srv] 抽卡骨架: 来自数据库（十连）")
        else:
            _gb1 = _db_template("_gacha_skeleton_single")
            if _gb1:
                srv.gacha_base = _gb1
                print("[srv] 抽卡骨架: 来自数据库（单抽）")
    except Exception as _e:
        print("[srv] 抽卡骨架加载失败:", _e)

    _auto_sync_master()
    _load_templates(srv)

    srv.gacha_variants = []
    try:
        import json as _json3
        _d = _json3.loads(_cfg_get("gacha_variants", "[]"))
        if isinstance(_d, list):
            srv.gacha_variants = [int(x) for x in _d]
            print("[srv] gacha 变体: %d 个 -> %s" % (len(srv.gacha_variants), srv.gacha_variants[:6]))
    except Exception as _e:
        print("[srv] gacha_variants 读取失败:", _e)

    srv.locked_paths = set()
    try:
        import json as _json2
        _data = _json2.loads(_cfg_get("locked_paths", "[]"))
        if isinstance(_data, list):
            srv.locked_paths = set(_data)
            print("[srv] locked_paths: %d 个 -> %s" % (len(srv.locked_paths), sorted(srv.locked_paths)))
    except Exception as _e:
        print("[srv] locked_paths 读取失败:", _e)
    srv.path_declared = {}
    try:
        import sqlite3 as _sq_pd
        _dbp = os.path.join(BASE_DIR, "offline.db")
        if os.path.exists(_dbp):
            _c = _sq_pd.connect(f"file:{_dbp}?mode=ro", uri=True, timeout=3)
            srv.path_declared = dict(_c.execute("SELECT path, declared FROM path_declared"))
            _c.close()
        if not srv.path_declared:
            import json as _json
            srv.path_declared = _json.load(open(os.path.join(BASE_DIR, "path_declared.json")))
        print("[srv] path_declared: %d 条（数据库）" % len(srv.path_declared))
    except Exception as _e:
        print("[srv] path_declared 读取失败:", _e)
    srv.proxy_mode = bool(getattr(a, "proxy", False))
    srv.fake_cache = {}

    srv.seq_map = {}
    srv.next_seq = 0
    import threading
    srv.lock = threading.Lock()

    # ===== 插件密钥通道（UDP，低延迟，无连接）=====
    # 每条报文一行 JSON：{"path":"...","key":"<32hex>","iv":"<32hex>"}
    # 服务器只保留最新一组，丢包无影响（下一条请求会带来新值）
    try:
        _udp_port = int(_cfg_get("key_udp_port", "827") or 827)
        threading.Thread(target=_key_channel_udp, args=(_udp_port,), daemon=True).start()
    except Exception as _e_udp:
        print(f"[keychan] 启动失败: {_e_udp}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        import json as _json
        _json.dump(srv.path_declared, open(os.path.join(BASE_DIR, "path_declared.json"), "w"), indent=2)
        print("[srv] 已保存 path_declared %d 条" % len(srv.path_declared))
    return 0


if __name__ == "__main__":
    sys.exit(main())
