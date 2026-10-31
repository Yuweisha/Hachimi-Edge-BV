"""静默 ConnectionResetError（客户端正常断开，不是错误）。"""
import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 在 class H 里加 handle() 覆写（放在 log_message 之后）
old = '''    def _serve(self):
        n = int(self.headers.get("Content-Length", 0) or 0)'''

new = '''    def handle(self):
        # 客户端（游戏/浏览器）用完会主动断开 keep-alive 连接，
        # BaseHTTPRequestHandler 会抛 ConnectionResetError 并打印 traceback。
        # 这是正常行为，静默掉。
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def _serve(self):
        n = int(self.headers.get("Content-Length", 0) or 0)'''

assert old in s, "_serve 未匹配"
s = s.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已静默连接重置错误")
