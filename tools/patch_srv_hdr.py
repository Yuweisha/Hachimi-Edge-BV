import io

p = 'C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py'
t = io.open(p, encoding='utf-8').read()

old = '''        self.log_message("%s -> %s (%d B req %d B)", rel or "/", src, len(data), len(body))'''

new = '''        self.log_message("%s -> %s (%d B req %d B)", rel or "/", src, len(data), len(body))
        # 首次请求打印完整头，便于对齐客户端期望
        if not getattr(H, "_logged_headers", False):
            H._logged_headers = True
            hdrs = "\\n".join("    %s: %s" % (k, v) for k, v in self.headers.items())
            self.log_message("--- 客户端请求头 ---\\n%s", hdrs)'''

assert old in t, '未匹配'
t = t.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('已加请求头日志')
