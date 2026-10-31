import io

p = 'C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py'
t = io.open(p, encoding='utf-8').read()

old = '''        if not self.server.hdr_logged:'''
new = '''        # 落盘请求体，便于分析
        if body:
            try:
                os.makedirs(r"C:/Users/Schwarz/srvreq", exist_ok=True)
                fn = safe or "root"
                with open(os.path.join(r"C:/Users/Schwarz/srvreq", fn + ".bin"), "wb") as fp:
                    fp.write(body)
            except Exception:
                pass

        if not self.server.hdr_logged:'''

assert old in t
t = t.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('已加请求体落盘')
