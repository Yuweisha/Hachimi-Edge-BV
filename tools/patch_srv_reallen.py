"""让本地服务器按 replay.bin 的真实长度构造假响应。

关键：CTR 流密码不改变长度，所以
    真实 srcSize = 36 + declared
构造同样长度的假体，客户端才会正常进入 0x3180；
插件在该层拦截并返回明文，完全绕过解密和哈希。
"""
from __future__ import annotations

import io
import re

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
t = io.open(P, encoding="utf-8").read()

# 1) 启动时读 replay.bin
anchor = "    srv.seq_map = {}"
assert anchor in t, "锚点未找到"

inject = '''    # 读 replay.bin：seq -> 明文长度
    srv.declared_by_seq = {}
    try:
        blob = open("C:/Users/Schwarz/uma_replay/replay.bin", "rb").read()
        if blob[:4] == b"RPLY":
            n = struct.unpack_from("<I", blob, 4)[0]
            off = 8
            for _ in range(n):
                sq, decl, dl = struct.unpack_from("<III", blob, off)
                off += 12
                srv.declared_by_seq[sq] = decl
                off += dl
            print("[srv] replay.bin: %d 条" % n)
    except Exception as e:
        print("[srv] replay.bin 读取失败:", e)

    srv.seq_map = {}'''

t = t.replace(anchor, inject, 1)

# 2) 响应体：36 + declared 字节，前 4 字节写 0x1000+seq
old = '''        data = struct.pack("<I", 0x1000 + seq) + b"\\x00" * 36'''
new = '''        # CTR 不改变长度：真实 srcSize = 36 + declared
        declared = self.server.declared_by_seq.get(seq, 512)
        raw = struct.pack("<I", 0x1000 + seq) + b"\\x00" * 32 + b"\\x00" * declared
        data = base64.b64encode(raw)'''
assert old in t, "响应体未匹配"
t = t.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("服务器：按 replay.bin 真实长度构造假响应")
