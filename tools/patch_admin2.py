"""把 admin_ui 挂进 local_server.py（修正锚点版本）。"""
import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
t = io.open(P, encoding="utf-8").read()

assert "admin_ui" not in t, "已经挂载过了"

# 1. import
anchor = 'PREFIX = "/umamusume/"'
assert anchor in t, "PREFIX 未找到"
t = t.replace(
    anchor,
    anchor + '\n\nsys.path.insert(0, r"C:/Users/Schwarz/projects/Hachimi-Edge/tools")\n'
             'from admin_ui import ADMIN_HTML, handle_api  # noqa: E402',
    1,
)

# 2. 路由：插在 _serve 里 path 解析之前
old = '''        path = urllib.parse.urlparse(self.path).path
        rel = path[len(PREFIX):] if path.startswith(PREFIX) else path.lstrip("/")'''
assert old in t, "_serve path 未匹配"

new = '''        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # ===== 管理界面 =====
        if path in ("/", "/admin", "/admin/"):
            body = ADMIN_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/api/"):
            code, ctype, body = handle_api(path, query)
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        rel = path[len(PREFIX):] if path.startswith(PREFIX) else path.lstrip("/")'''

t = t.replace(old, new, 1)

# 3. 启动提示
old2 = '    print(f"录制库 {n} 个接口，监听 http://{a.host}:{a.port}")'
assert old2 in t, "启动提示未匹配"
t = t.replace(
    old2,
    old2 + '\n    print(f"[srv] 管理界面: http://{a.host}:{a.port}/admin", flush=True)',
    1,
)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("已挂载管理界面")
