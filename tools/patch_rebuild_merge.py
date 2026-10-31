"""三处改动：
1. 服务器 proxy 模式下 path_declared 实时落盘（不等退出）
2. rebuild_merge 不覆盖已有条目（只加新接口）
3. 新接口自动进入 path_declared
"""
import io

# ---------- 1. 服务器实时落盘 ----------
p1 = "tools/local_server.py"
s = io.open(p1, encoding="utf-8").read()
old = '''                    self.server.path_declared[rel] = decl
                    self.log_message("proxy %s -> declared=%d (raw=%d)", rel, decl, len(raw))'''
new = '''                    self.server.path_declared[rel] = decl
                    self.log_message("proxy %s -> declared=%d (raw=%d)", rel, decl, len(raw))
                    # 实时落盘：力杀进程也不会丢
                    try:
                        _json.dump(self.server.path_declared,
                                   open("C:/Users/Schwarz/uma_replay/path_declared.json", "w"),
                                   indent=2, ensure_ascii=False)
                    except Exception:
                        pass'''
assert old in s, "proxy 记录块未匹配"
s = s.replace(old, new, 1)
io.open(p1, "w", encoding="utf-8", newline="\n").write(s)
print("1. 服务器已改为实时落盘")

# ---------- 2. rebuild_merge：不覆盖已有 ----------
p2 = "tools/rebuild_merge.py"
s = io.open(p2, encoding="utf-8").read()

old2 = '''        if decl in old and old[decl] == data:
            skipped += 1
            continue
        if decl in old:
            updated += 1
        else:
            added += 1
        old[decl] = data'''
new2 = '''        if decl in old:
            # 已有条目：一律保留旧数据（含手工注入的金币/剧情等）
            skipped += 1
            continue
        added += 1
        old[decl] = data'''
assert old2 in s, "合并逻辑未匹配"
s = s.replace(old2, new2, 1)

# 匹配不到路径的新接口：用文件名 + 长度登记
old3 = '''        if api is None:
            # 新接口：采用文件长度作为 declared（服务器首见时会给这个值）
            api = stem.split("_", 1)[-1]
            print(f"  [新] {api} (declared={len(data)} 由文件长度推定)")
            new_decl[api] = len(data)
            decl = len(data)'''
new3 = '''        if api is None:
            # 匹配不到已知路径：这是本次新见到的接口
            # 用响应里的顶层 key 或文件名登记，declared 取数据长度
            api = stem.split("_", 1)[-1]
            if api.startswith("resp"):
                api = f"unknown/{api}"
            print(f"  [新接口] {api}  declared={len(data)}")
            new_decl[api] = len(data)
            decl = len(data)'''
assert old3 in s, "新接口分支未匹配"
s = s.replace(old3, new3, 1)
io.open(p2, "w", encoding="utf-8", newline="\n").write(s)
print("2. rebuild_merge 已改为只加不覆盖")
