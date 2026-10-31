"""rebuild_merge：改用「长度 → 路径」反查（插件文件名不可靠）。"""
import io

P = "tools/rebuild_merge.py"
s = io.open(P, encoding="utf-8").read()

old = '''def name_to_path(fname_stem: str, paths: list[str]) -> str | None:
    """从 0003_support_card_get_extend_master_info 反查 support_card/get_extend_master_info。"""
    body = fname_stem.split("_", 1)[-1]
    # 精确：路径全部斜杠换下划线后等于 body
    hits = [p for p in paths if p.replace("/", "_") == body]
    if len(hits) == 1:
        return hits[0]
    # 前缀/包含匹配
    hits = [p for p in paths if body.endswith(p.replace("/", "_")) or p.replace("/", "_").endswith(body)]
    if len(hits) == 1:
        return hits[0]
    return hits[0] if hits else None'''

new = '''def path_by_length(length: int, decl: dict[str, int]) -> str | None:
    """按数据长度反查路径（插件落盘的文件名不可靠，只能靠长度）。"""
    hits = [p for p, v in decl.items() if v == length]
    if len(hits) == 1:
        return hits[0]
    return None'''

assert old in s, "name_to_path 未匹配"
s = s.replace(old, new, 1)

# 调用处：先用长度匹配，失败再退回文件名
old2 = '''        api = name_to_path(stem, known_paths)'''
new2 = '''        api = path_by_length(len(data), cur_decl)
        if api is None:
            # 长度也对不上：退回文件名匹配
            body = stem.split("_", 1)[-1]
            hits = [p for p in known_paths if p.replace("/", "_") == body]
            api = hits[0] if len(hits) == 1 else None'''
assert old2 in s, "调用点未匹配"
s = s.replace(old2, new2, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已改为按长度反查路径")
