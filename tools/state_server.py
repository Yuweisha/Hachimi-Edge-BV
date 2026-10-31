"""状态化服务端：录制模板 + state 注入。

与 local_server.py 的区别：
  local_server  = 每个接口返回录死的明文（快照，导航会不一致）
  state_server  = 所有接口共享一份 state.json，读接口从 state 注入

当前实现：
  - load/index      → 模板 + 用 state 覆盖 coin_info / item_list / tp_info / rp_info
  - start_session   → 模板（sid 保持录制值，避免会话不匹配）
  - 其他接口        → 模板原样
"""
from __future__ import annotations

import base64
import glob
import http.server
import json
import os
import struct
import sys
import threading
import urllib.parse

import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"
REPLAY = r"C:/Users/Schwarz/uma_replay"
STATE = os.path.join(REPLAY, "state.json")
PREFIX = "/umamusume"

# ---------- state / 模板 ----------

state = {}
templates = {}      # path -> msgpack bytes
declared = {}       # path -> 明文长度


def load_state():
    global state
    try:
        state = json.load(open(STATE, encoding="utf-8"))
        print(f"[state] {len(state)} 个顶层键")
    except Exception as e:
        print("[state] 读取失败:", e)
        state = {}


def find_newest(name_hint: str, min_size: int = 0):
    cands = [f for f in glob.glob(os.path.join(GD, "hachimi/http/*/*.msgpack"))
             if os.path.getsize(f) >= min_size]
    cands = [f for f in cands if name_hint in os.path.basename(f)]
    return max(cands, key=os.path.getmtime) if cands else None


def build_templates():
    """路径 -> 模板。用抓包文件名反推路径（名字可能猜错，按大小兜底）。"""
    load_state()

    mapping = [
        ("tool/start_session", find_newest("start_session"), 400),
        ("load/index", find_newest("load_index", 1_200_000), 1_200_000),
        ("read_info/index", find_newest("home_story_data_array", 50_000), 50_000),
        ("support_card/get_extend_master_info", find_newest("event_skill_info", 50_000), 50_000),
        ("live_theater/index", find_newest("live_theater", 5000), 5000),
        ("gacha/index", find_newest("gacha_info_list", 2000), 2000),
    ]
    for path, f, minsz in mapping:
        if not f or os.path.getsize(f) < minsz:
            print(f"[tpl] {path}: 未找到")
            continue
        b = open(f, "rb").read()
        templates[path] = b
        declared[path] = len(b)
        print(f"[tpl] {path}: {len(b)} B")

    print(f"[tpl] 共 {len(templates)} 个")


# ---------- 注入 ----------

def inject_load_index(raw: bytes) -> bytes:
    """把 state 里的动态字段写回 load/index 的 msgpack。"""
    try:
        v = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    except Exception as e:
        print("[inject] 解析失败:", e)
        return raw
    if not isinstance(v, dict) or not isinstance(v.get("data"), dict):
        return raw
    d = v["data"]

    for k in ("coin_info", "tp_info", "rp_info", "user_info", "item_list"):
        if k in state:
            d[k] = state[k]

    try:
        out = msgpack.packb(v, use_bin_type=True)
        print(f"[inject] load/index {len(raw)} -> {len(out)} B")
        return out
    except Exception as e:
        print("[inject] 打包失败:", e)
        return raw


# ---------- HTTP ----------

def write_replay():
    """把模板（含 state 注入）写成 replay.bin，供插件按 declared 查。"""
    import struct as _st
    items = []
    for path, raw in templates.items():
        if path == "load/index":
            raw = inject_load_index(raw)
        items.append((len(raw), raw))
    items.sort(key=lambda x: x[0])

    out = os.path.join(REPLAY, "replay.bin")
    with open(out, "wb") as fp:
        fp.write(b"RPLY")
        fp.write(_st.pack("<I", len(items)))
        for decl, data in items:
            fp.write(_st.pack("<III", decl, decl, len(data)))
            fp.write(data)
    print(f"[replay] 已写 {out}，{len(items)} 条")
    for decl, _ in items:
        print(f"  {decl}")


def _serve_placeholder():
    pass


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[srv]", fmt % args, flush=True)

    def _rel(self) -> str:
        p = urllib.parse.urlparse(self.path).path
        rel = p[len(PREFIX):] if p.startswith(PREFIX) else p.lstrip("/")
        while "//" in rel:
            rel = rel.replace("//", "/")
        return rel.strip("/")

    def _serve(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n:
            self.rfile.read(n)

        rel = self._rel()
        decl = declared.get(rel)

        if decl is None:
            print(f"[srv] {rel} -> UNKNOWN(empty)", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msgpack")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        # 假体：36 + declared 字节，前 4 字节 = declared
        raw = struct.pack("<I", decl) + b"\x00" * 32 + b"\x00" * decl
        body = base64.b64encode(raw)

        self.send_response(200)
        self.send_header("Content-Type", "application/x-msgpack")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(f"[srv] {rel} -> declared={decl}", flush=True)

    do_POST = _serve
    do_GET = _serve


def main() -> int:
    port = 8080
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])

    build_templates()
    write_replay()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"[srv] listening :{port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
