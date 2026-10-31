import io

p = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
s = io.open(p, encoding="utf-8").read()

BS = chr(92)
old = (
    "    def log_message(self, fmt, *args):\n"
    '        sys.stderr.write("[srv] %s' + BS + 'n" % (fmt % args))\n'
)
new = (
    "    def log_message(self, fmt, *args):\n"
    "        msg = fmt % args\n"
    '        if "/api/" in msg or "/admin" in msg:\n'
    "            return\n"
    '        sys.stderr.write("[srv] %s' + BS + 'n" % msg)\n'
)

assert old in s, "log_message 未匹配:\n" + repr(s[s.find("def log_message"):s.find("def log_message")+200])
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("已静音管理请求")
