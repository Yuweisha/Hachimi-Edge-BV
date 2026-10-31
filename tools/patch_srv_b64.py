import io

p = 'C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py'
t = io.open(p, encoding='utf-8').read()

old = '''        if os.path.exists(f):
            data = open(f, "rb").read()
            src = "resp.bin"
        elif os.path.exists(f64):
            data = base64.b64decode(open(f64, "r").read().strip())
            src = "resp.b64"
        else:
            data = FALLBACK
            src = "FALLBACK"'''

new = '''        # 注意：客户端收发都是 base64 文本，必须原文返回 resp.b64
        if os.path.exists(f64):
            data = open(f64, "rb").read().strip()
            src = "resp.b64(TEXT)"
        elif os.path.exists(f):
            data = base64.b64encode(open(f, "rb").read())
            src = "resp.bin->b64"
        else:
            data = base64.b64encode(FALLBACK)
            src = "FALLBACK(b64)"'''

assert old in t, '未匹配'
t = t.replace(old, new, 1)

# Content-Type 也改成文本
t = t.replace('self.send_header("Content-Type", "application/octet-stream")',
              'self.send_header("Content-Type", "application/x-msgpack")', 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('已改为返回 base64 文本')
