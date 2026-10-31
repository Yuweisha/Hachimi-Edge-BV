"""服务器对 gacha/exec 每次随机返回一个变体 declared（实现随机抽卡）。"""
import io

P = "tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 启动时读变体清单
old = '''    srv.locked_paths = set()'''
new = '''    srv.gacha_variants = []
    try:
        import json as _json3
        _vf = "C:/Users/Schwarz/uma_replay/gacha_variants.json"
        _d = _json3.load(open(_vf, encoding="utf-8"))
        if isinstance(_d, list):
            srv.gacha_variants = [int(x) for x in _d]
            print("[srv] gacha 变体: %d 个 -> %s" % (len(srv.gacha_variants), srv.gacha_variants[:6]))
    except Exception:
        pass
    srv.locked_paths = set()'''
assert old in s, "locked_paths 初始化未匹配"
s = s.replace(old, new, 1)

# 回放时对 gacha/exec 随机选变体
old2 = '''            # 回放：按路径查 declared
            decl = self.server.path_declared.get(rel)
            if decl is None:'''
new2 = '''            # 回放：按路径查 declared
            decl = self.server.path_declared.get(rel)
            # 抽卡：每次随机选一个变体，让结果不同
            if rel == "gacha/exec" and getattr(self.server, "gacha_variants", None):
                import random as _rnd
                decl = _rnd.choice(self.server.gacha_variants)
                self.log_message("replay %s -> 随机变体 declared=%d", rel, decl)
            if decl is None:'''
assert old2 in s, "回放分支未匹配"
s = s.replace(old2, new2, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已加抽卡随机变体")
