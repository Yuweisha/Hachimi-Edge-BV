"""服务器支持 declared=0（IsCompressed=false）的接口：
proxy 记录时用 -明文长度 编码；回放时返回 [0][32B 零][明文长度 零]。
"""
import io

P = "tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 1) proxy 记录：decl == 0 时改记为 -明文长度
old1 = '''                if len(raw) >= 4:
                    decl = struct.unpack_from("<I", raw, 0)[0]
                    self.server.path_declared[rel] = decl'''
new1 = '''                if len(raw) >= 4:
                    decl = struct.unpack_from("<I", raw, 0)[0]
                    if decl == 0 and len(raw) > 36:
                        # IsCompressed=false：明文长度 = 总长 - 36
                        # 用负数编码，回放时据此返回等长假体
                        decl = -(len(raw) - 36)
                    self.server.path_declared[rel] = decl'''
assert old1 in s, "proxy 记录块未匹配"
s = s.replace(old1, new1, 1)

# 2) 回放：decl < 0 时返回 [0][32B 零][plain 零]
old2 = '''            elif decl == 0:
                # 在线时就是空响应，回放也返回空 body（客户端不会进 0x3180）
                self.log_message("replay %s -> EMPTY(0)", rel)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return'''
new2 = '''            elif decl < 0:
                # IsCompressed=false 的接口（trainer_note / save_voice 等）
                # 客户端会调 0x3180，srcSize = 36 + 明文长度
                plain = -decl
                body = b"\\x00\\x00\\x00\\x00" + b"\\x00" * 32 + b"\\x00" * plain
                self.log_message("replay %s -> UNCOMPRESSED(%d)", rel, plain)
                import base64 as _b64
                payload = _b64.b64encode(body)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if not self._is_head():
                    self.wfile.write(payload)
                return
            elif decl == 0:
                # 真正的空响应
                self.log_message("replay %s -> EMPTY(0)", rel)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-msgpack")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return'''
assert old2 in s, "回放 decl==0 分支未匹配"
s = s.replace(old2, new2, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("服务器已支持 declared=0 回放")
