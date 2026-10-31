"""服务器加 /dynamic/<n> 路由：返回 dynamic/<n>.msgpack 原始字节。

插件在 replay.bin 查不到 declared 时，通过 HTTPS 拉这个接口。
"""
import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 找到 rel 计算之后的位置插入
anchor = '''        rel = rel.strip("/")'''
assert anchor in s, "rel 锚点未匹配"

new = anchor + '''

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
                    return'''

s = s.replace(anchor, new, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已加 /dynamic/<n> 路由")
