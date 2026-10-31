"""给本地服务器加两种模式：

--proxy   转发到真实服务器，记录「路径 -> declared(src[0:4])」，同时原样返回
--replay  按路径查 declared，构造 36+declared 字节假体（前 4 字节 = declared）

这样路径标识由服务器保证稳定，插件只需按 declared 查 replay.bin。
"""
from __future__ import annotations

import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
t = io.open(P, encoding="utf-8").read()

# 1) 读路径表 + 模式常量
anchor = "    srv.seq_map = {}"
inject = '''    # 路径 -> declared 表
    srv.path_declared = {}
    try:
        import json as _json
        srv.path_declared = _json.load(open("C:/Users/Schwarz/uma_replay/path_declared.json"))
        print("[srv] path_declared: %d 条" % len(srv.path_declared))
    except Exception:
        pass
    srv.proxy_mode = bool(getattr(a, "proxy", False))

    srv.seq_map = {}'''
assert anchor in t
t = t.replace(anchor, inject, 1)

# 2) 响应逻辑：proxy 转发 / replay 用 path_declared
old_start = t.index('        # 每个接口第一次出现时分配序号（按请求顺序）')
old_end = t.index('        self.send_response(200)')

new_block = '''        seq = 0
        if self.server.proxy_mode:
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
            import base64 as _b64
            try:
                raw = _b64.b64decode(data)
                if len(raw) >= 4:
                    decl = struct.unpack_from("<I", raw, 0)[0]
                    self.server.path_declared[rel] = decl
                    self.log_message("proxy %s -> declared=%d", rel, decl)
            except Exception:
                pass
        else:
            # 回放：按路径查 declared
            decl = self.server.path_declared.get(rel)
            if decl is None:
                decl = self.server.declared_by_seq.get(seq, 512)
                self.log_message("replay %s -> MISS(默认 %d)", rel, decl)
            raw = struct.pack("<I", decl) + b"\\x00" * 32 + b"\\x00" * decl
            import base64 as _b64
            data = _b64.b64encode(raw)

'''
t = t[:old_start] + new_block + t[old_end:]

# 3) 命令行参数
t = t.replace('    a = ap.parse_args()',
              '    ap.add_argument("--proxy", action="store_true")\n    a = ap.parse_args()', 1)

# 4) 退出时保存 path_declared
t = t.replace('    srv.serve_forever()',
'''    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        import json as _json
        _json.dump(srv.path_declared, open("C:/Users/Schwarz/uma_replay/path_declared.json", "w"), indent=2)
        print("[srv] 已保存 path_declared %d 条" % len(srv.path_declared))''', 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("服务器已支持 --proxy / 回放（按路径）")
