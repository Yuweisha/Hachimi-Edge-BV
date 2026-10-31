"""给 proxy 模式加原始响应落盘，用于诊断 note/trainer_note。"""
import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
t = io.open(P, encoding="utf-8").read()

old = '''            import base64 as _b64
            try:
                raw = _b64.b64decode(data)
                if len(raw) >= 4:
                    decl = struct.unpack_from("<I", raw, 0)[0]
                    self.server.path_declared[rel] = decl
                    self.log_message("proxy %s -> declared=%d", rel, decl)
            except Exception:
                pass'''

new = '''            import base64 as _b64
            # 落盘原始响应（诊断用）
            try:
                import os as _os
                dd = "C:/Users/Schwarz/uma_replay/raw"
                _os.makedirs(dd, exist_ok=True)
                safe = rel.replace("/", "_")
                open(f"{dd}/{safe}.raw", "wb").write(data)
                self.log_message("raw saved: %s (%d B)", safe, len(data))
            except Exception:
                pass
            try:
                raw = _b64.b64decode(data)
                if len(raw) >= 4:
                    decl = struct.unpack_from("<I", raw, 0)[0]
                    self.server.path_declared[rel] = decl
                    self.log_message("proxy %s -> declared=%d (raw=%d)", rel, decl, len(raw))
                else:
                    self.log_message("proxy %s -> 响应太短 raw=%d body=%r", rel, len(raw), data[:80])
            except Exception as e:
                self.log_message("proxy %s -> base64 失败: %s body=%r", rel, e, data[:80])'''

assert old in t, '未匹配'
t = t.replace(old, new, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("已加原始响应落盘")
