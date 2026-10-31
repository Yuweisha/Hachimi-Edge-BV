import io

p = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
s = io.open(p, encoding="utf-8").read()

# 1. 去掉 admin 的 print
old1 = '            print(f"[admin] {path} -> {len(body)} B", flush=True)\n'
if old1 in s:
    s = s.replace(old1, "", 1)
    print("已移除 admin print")

# 2. favicon 返回 204
old2 = '''        if path.startswith("/api/"):'''
new2 = '''        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path.startswith("/api/"):'''
assert old2 in s, "/api/ 路由未匹配"
s = s.replace(old2, new2, 1)
print("已加 favicon 204")

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
