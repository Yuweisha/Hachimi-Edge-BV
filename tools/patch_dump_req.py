"""服务器 proxy 模式落盘请求体，用于分析抽卡等接口的入参格式。"""
import io

P = "tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 在读取请求体之后、转发之前落盘
old = '''            import base64 as _b64
            # 落盘原始响应（诊断用）'''
new = '''            # 落盘请求体（诊断用，便于分析入参格式）
            try:
                import os as _os2
                rd = "C:/Users/Schwarz/uma_replay/req"
                _os2.makedirs(rd, exist_ok=True)
                rsafe = rel.replace("/", "_")
                with open(f"{rd}/{rsafe}.req", "wb") as _f:
                    _f.write(req_body)
            except Exception:
                pass

            import base64 as _b64
            # 落盘原始响应（诊断用）'''
assert old in s, "落盘锚点未匹配"
s = s.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已加请求体落盘")
