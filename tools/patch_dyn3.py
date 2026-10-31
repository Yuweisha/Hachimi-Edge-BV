"""服务器：gacha/exec 每次现场生成随机数据写入 dynamic/<declared>.msgpack。

替换旧的「随机选变体」逻辑。
"""
import io

P = "tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 1) 替换旧的变体逻辑
old = '''            # 抽卡：每次随机选一个变体，让结果不同
            if rel == "gacha/exec" and getattr(self.server, "gacha_variants", None):
                import random as _rnd
                decl = _rnd.choice(self.server.gacha_variants)
                self.log_message("replay %s -> 随机变体 declared=%d", rel, decl)'''
new = '''            # 抽卡：现场生成随机结果，写 dynamic/<declared>.msgpack
            if rel == "gacha/exec" and decl and decl > 0:
                try:
                    base = getattr(self.server, "gacha_base", None)
                    if base:
                        dyn = make_dynamic_gacha(base, decl)
                        if dyn:
                            self.log_message("replay %s -> 现场生成（declared=%d）", rel, decl)
                except Exception as e:
                    self.log_message("replay %s 生成失败: %s", rel, e)'''
assert old in s, "变体逻辑未匹配"
s = s.replace(old, new, 1)

# 2) make_dynamic_gacha 增加 declared 参数（写到 dynamic/<declared>.msgpack）
old2 = '''def make_dynamic_gacha(base_resp):
    """生成动态抽卡响应，返回 (declared, seq)。"""'''
new2 = '''def make_dynamic_gacha(base_resp, declared):
    """生成动态抽卡响应，写到 dynamic/<declared>.msgpack，返回 seq。"""'''
assert old2 in s
s = s.replace(old2, new2, 1)

old3 = '''    os.makedirs(DYNAMIC_DIR, exist_ok=True)
    seq = _dyn_seq[0] = _dyn_seq[0] + 1
    open(f"{DYNAMIC_DIR}/{seq}.msgpack", "wb").write(data)

    stat = {}
    for _, _, r in cards:
        stat[r] = stat.get(r, 0) + 1
    print(f"[srv] 抽卡 gacha_id={gacha_id} n={n} -> {stat} (seq={seq}, {len(data)} B)", flush=True)
    return (0xFFFF0000 + seq, seq)'''
new3 = '''    # 长度必须 <= declared，客户端 dst_cap 通常是 declared 的 2 倍
    if len(data) > declared:
        print(f"[srv] 抽卡数据 {len(data)} B 超过 declared {declared}，截断失败", flush=True)
        return None

    os.makedirs(DYNAMIC_DIR, exist_ok=True)
    path = f"{DYNAMIC_DIR}/{declared}.msgpack"
    open(path, "wb").write(data)

    stat = {}
    for _, _, r in cards:
        stat[r] = stat.get(r, 0) + 1
    print(f"[srv] 抽卡 gacha_id={gacha_id} n={n} -> {stat} ({len(data)} B -> {path})", flush=True)
    return True'''
assert old3 in s, "写入逻辑未匹配"
s = s.replace(old3, new3, 1)

# 3) 启动时加载 gacha 骨架
old4 = '''    srv.gacha_variants = []'''
new4 = '''    # 抽卡骨架：从 replay.bin 里找一份含 gacha_result_list 的响应
    srv.gacha_base = None
    try:
        import struct as _st
        import msgpack as _mp
        _rb = open("C:/Users/Schwarz/uma_replay/replay.bin", "rb").read()
        _n = _st.unpack_from("<I", _rb, 4)[0]
        _off = 8
        for _ in range(_n):
            _a, _d, _dl = _st.unpack_from("<III", _rb, _off)
            _off += 12
            _payload = _rb[_off:_off + _dl]
            _off += _dl
            try:
                _v = _mp.unpackb(_payload, raw=False, strict_map_key=False, unicode_errors="replace")
            except Exception:
                continue
            _dd = _v.get("data", {}) if isinstance(_v, dict) else {}
            if isinstance(_dd, dict) and "gacha_result_list" in _dd:
                srv.gacha_base = _v
                print("[srv] 抽卡骨架: %d B (declared=%d)" % (_dl, _d))
                break
    except Exception as _e:
        print("[srv] 加载抽卡骨架失败:", _e)

    srv.gacha_variants = []'''
assert old4 in s, "gacha_variants 初始化未匹配"
s = s.replace(old4, new4, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("服务器已改为现场生成")
