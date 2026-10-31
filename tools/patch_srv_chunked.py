import io

p = 'C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py'
t = io.open(p, encoding='utf-8').read()

old = '''        self.send_response(200)
        self.send_header("Content-Type", "application/x-msgpack")
        self.send_header("Content-Encoding", "identity")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "keep-alive")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)'''

new = '''        self.send_response(200)
        self.send_header("Content-Type", "application/x-msgpack")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        # chunked 分块写
        self.wfile.write(b"%x\\r\\n" % len(data) + data + b"\\r\\n")
        self.wfile.write(b"0\\r\\n\\r\\n")'''

assert old in t, '未匹配'
t = t.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('已改为 chunked')
