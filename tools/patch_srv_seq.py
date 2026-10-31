import io

p = 'C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py'
t = io.open(p, encoding='utf-8').read()

# 替换整个 _serve 为「序号模式」
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

        # 每个接口第一次出现时分配序号（按请求顺序）
        with self.server.lock:
            if rel not in self.server.seq_map:
                self.server.seq_map[rel] = self.server.next_seq
                self.server.next_seq += 1
            seq = self.server.seq_map[rel]

        self.log_message("%s -> seq=%d", rel or "/", seq)

        # 返回 [u32 seq][36 字节填充]，共 40 字节
        # 插件读 src[0:4] 得到 seq，直接命中 replay.bin
        data = struct.pack("<I", seq) + b"\\x00" * 36

        self.send_response(200)
        self.send_header("Content-Type", "application/x-msgpack")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(b"%x\\r\\n" % len(data) + data + b"\\r\\n")
        self.wfile.write(b"0\\r\\n\\r\\n")

'''

t = t[:start] + new + t[end:]

# import struct
if 'import struct' not in t:
    t = t.replace('import base64\n', 'import base64\nimport struct\n', 1)

# 初始化 server 属性
t = t.replace('''    srv = http.server.ThreadingHTTPServer((a.host, a.port), H)
    srv.hdr_logged = False''',
'''    srv = http.server.ThreadingHTTPServer((a.host, a.port), H)
    srv.hdr_logged = False
    srv.seq_map = {}
    srv.next_seq = 0
    import threading
    srv.lock = threading.Lock()''', 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('已改为序号模式')
