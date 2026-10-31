"""锁定接口：proxy 模式不覆盖已锁定的 declared，回放永远用锁定的值。

用法：
  写入 locked_paths.json，比如 ["load/index"]
  列表里的路径在 proxy 模式下不会被真实响应的 declared 覆盖。
"""
import io

P = "tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 1) 启动时读 locked_paths.json
old = '''    srv.path_declared = {}'''
new = '''    srv.locked_paths = set()
    try:
        import json as _json2
        _lp = "C:/Users/Schwarz/uma_replay/locked_paths.json"
        _data = _json2.load(open(_lp, encoding="utf-8"))
        if isinstance(_data, list):
            srv.locked_paths = set(_data)
            print("[srv] locked_paths: %d 个 -> %s" % (len(srv.locked_paths), sorted(srv.locked_paths)))
    except Exception:
        pass
    srv.path_declared = {}'''
assert old in s, "srv.path_declared 初始化未匹配"
s = s.replace(old, new, 1)

# 2) proxy 记录时跳过锁定路径
old2 = '''                    if decl == 0 and len(raw) > 36:
                        # IsCompressed=false：明文长度 = 总长 - 36
                        # 用负数编码，回放时据此返回等长假体
                        decl = -(len(raw) - 36)
                    self.server.path_declared[rel] = decl'''
new2 = '''                    if decl == 0 and len(raw) > 36:
                        # IsCompressed=false：明文长度 = 总长 - 36
                        # 用负数编码，回放时据此返回等长假体
                        decl = -(len(raw) - 36)
                    if rel in getattr(self.server, "locked_paths", set()):
                        self.log_message("proxy %s -> declared=%d (锁定，不覆盖)", rel, decl)
                    else:
                        self.server.path_declared[rel] = decl'''
assert old2 in s, "proxy 记录块未匹配"
s = s.replace(old2, new2, 1)

# 3) 实时落盘也要跳过（放在同一个 else 分支里，这里调整缩进）
old3 = '''                    self.log_message("proxy %s -> declared=%d (raw=%d)", rel, decl, len(raw))
                    # 实时落盘：力杀进程也不会丢
                    try:
                        _json.dump(self.server.path_declared,
                                   open("C:/Users/Schwarz/uma_replay/path_declared.json", "w"),
                                   indent=2, ensure_ascii=False)
                    except Exception:
                        pass'''
new3 = '''                    if rel not in getattr(self.server, "locked_paths", set()):
                        # 实时落盘：力杀进程也不会丢
                        try:
                            _json.dump(self.server.path_declared,
                                       open("C:/Users/Schwarz/uma_replay/path_declared.json", "w"),
                                       indent=2, ensure_ascii=False)
                        except Exception:
                            pass'''
assert old3 in s, "实时落盘块未匹配"
s = s.replace(old3, new3, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已加锁定机制")
