import io

p = 'C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py'
t = io.open(p, encoding='utf-8').read()

start = t.index('    def _serve(self):')
end = t.index('    def do_POST(self):')

new = '''    def _serve(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n) if n else b""

        path = urllib.parse.urlparse(self.path).path
        rel = path[len(PREFIX):] if path.startswith(PREFIX) else path.lstrip("/")
        rel = rel.replace("\\x00", "")
        while "//" in rel:
            rel = rel.replace("//", "/")
        rel = rel.strip("/")
        safe = rel.replace("/", "__").strip("_")
        d = os.path.join(DB, safe)
        f = os.path.join(d, "resp.bin")
        f64 = os.path.join(d, "resp.b64")

        if os.path.exists(f):
            data = open(f, "rb").read()
            src = "resp.bin"
        elif os.path.exists(f64):
            data = base64.b64decode(open(f64, "r").read().strip())
            src = "resp.b64"
        else:
            data = FALLBACK
            src = "FALLBACK"

        self.log_message("%s -> %s (%d B req %d B)", rel or "/", src, len(data), len(body))

        if not self.server.hdr_logged:
            self.server.hdr_logged = True
            self.log_message("--- 客户端请求头 ---")
            for k, v in self.headers.items():
                self.log_message("    %s: %s", k, v)

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Encoding", "identity")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "keep-alive")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

'''

t = t[:start] + new + t[end:]

# 加 server 属性初始化
old_main = '''    srv = http.server.ThreadingHTTPServer((a.host, a.port), H)'''
new_main = '''    srv = http.server.ThreadingHTTPServer((a.host, a.port), H)
    srv.hdr_logged = False'''
t = t.replace(old_main, new_main, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('已重写 _serve')
