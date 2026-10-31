"""给 local_server 的假体生成加缓存，避免每次请求都重建 1.2MB+ 的 base64。"""
import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
t = io.open(P, encoding="utf-8").read()

# 1. 初始化缓存
anchor = "    srv.proxy_mode = bool(getattr(a, \"proxy\", False))"
assert anchor in t, "锚点未找到"
t = t.replace(anchor, anchor + "\n    srv.fake_cache = {}", 1)

# 2. 假体构造改用缓存
old = '''            vid = 0
            try:
                vid = int(self.headers.get("ViewerID", "0") or 0)
            except Exception:
                vid = 0
            # 假体：36+declared，前 4 字节 declared，4-8 字节 viewer_id（插件据此改明文）
            raw = struct.pack("<II", decl, vid) + b"\\x00" * 28 + b"\\x00" * decl
            import base64 as _b64
            data = _b64.b64encode(raw)'''

new = '''            vid = 0
            try:
                vid = int(self.headers.get("ViewerID", "0") or 0)
            except Exception:
                vid = 0
            # 假体缓存：同 (decl, vid) 只构造一次，后续直接复用
            key = (decl, vid)
            data = self.server.fake_cache.get(key)
            if data is None:
                raw = struct.pack("<II", decl, vid) + b"\\x00" * 28 + b"\\x00" * decl
                import base64 as _b64
                data = _b64.b64encode(raw)
                self.server.fake_cache[key] = data'''

assert old in t, "假体构造未匹配"
t = t.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("已加假体缓存")
