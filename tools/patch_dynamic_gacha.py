"""服务器：gacha/exec 现场生成随机抽卡结果（不用模板）。

流程：
1. 读 reqplain/ 下最新的请求明文，解析 gacha_id 和抽卡次数
2. 按稀有度权重抽卡（角色/支援各自 3%/18%/79%）
3. 生成完整响应 → 写 dynamic/<seq>.msgpack
4. 返回 declared = 0xFFFF0000 + seq
"""
import io

P = "tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

# 1) 加抽卡生成模块（放在 imports 之后）
anchor = '''DB = "hachimi"'''
if anchor not in s:
    anchor = '''def _game_alive'''
    # admin_ui 在另一个文件，这里用文件末尾插入函数

gacha_code = '''

# ---------- 抽卡现场生成 ----------
import sqlite3 as _sqlite3

GACHA_DB = "C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
REQPLAIN_DIR = "C:/Users/Schwarz/uma_replay/reqplain"
DYNAMIC_DIR = "C:/Users/Schwarz/uma_replay/dynamic"
RARITY_W = {3: 0.03, 2: 0.18, 1: 0.79}
_dyn_seq = [0]


def _latest_req_plain():
    """取 reqplain 下最新写入的请求明文。"""
    try:
        import glob as _g
        files = _g.glob(REQPLAIN_DIR + "/req_*.msgpack")
        if not files:
            return None
        return max(files, key=os.path.getmtime)
    except Exception:
        return None


def _parse_gacha_req(path):
    """从请求明文里解析 gacha_id / draw_num。"""
    try:
        import msgpack as _mp
        v = _mp.unpackb(open(path, "rb").read(), raw=False, strict_map_key=False,
                        unicode_errors="replace")
    except Exception:
        return None
    # 常见结构：{gacha_id: N, draw_type: 1|2, ...} 或嵌在 data 里
    def walk(o, depth=0):
        if depth > 4:
            return {}
        out = {}
        if isinstance(o, dict):
            for k, val in o.items():
                if k in ("gacha_id", "draw_type", "draw_num", "gacha_draw_type", "count"):
                    if isinstance(val, int):
                        out[k] = val
                elif isinstance(val, (dict, list)):
                    out.update(walk(val, depth + 1))
        elif isinstance(o, list):
            for x in o[:4]:
                out.update(walk(x, depth + 1))
        return out
    return walk(v)


def _draw_cards(gacha_id, n):
    """按权重抽 n 张。返回 [(card_id, card_type, rarity)]。"""
    import random as _r
    try:
        con = _sqlite3.connect(GACHA_DB)
        cur = con.cursor()
        cur.execute("SELECT card_id, card_type, rarity FROM gacha_available WHERE gacha_id=?",
                    (gacha_id,))
        rows = cur.fetchall()
        con.close()
    except Exception:
        return []
    if not rows:
        return []

    pools = {}
    for cid, ct, rar in rows:
        pools.setdefault((ct, rar), []).append(cid)

    # 按 card_type 分组（1=角色, 2=支援）
    by_type = {}
    for (ct, rar), lst in pools.items():
        by_type.setdefault(ct, {})[rar] = lst

    out = []
    for _ in range(n):
        # 用主类型（角色池或支援池）——优先 card_type=1，否则取第一个
        ct = 1 if 1 in by_type else next(iter(by_type))
        rp = by_type[ct]
        rs = [r for r in rp if r in RARITY_W]
        if not rs:
            continue
        ws = [RARITY_W[r] for r in rs]
        r = _r.choices(rs, weights=ws, k=1)[0]
        cid = _r.choice(rp[r])
        out.append((cid, ct, r))
    return out


def _build_gacha_response(gacha_id, cards, base_resp):
    """基于一份响应骨架填抽卡结果。"""
    import copy as _copy
    v = _copy.deepcopy(base_resp)
    d = v.setdefault("data", {})
    results = []
    add_pieces = {}
    for cid, ct, rar in cards:
        results.append({
            "card_type": ct,
            "card_id": cid,
            "piece_id": cid if ct == 1 else 0,
            "common_item_category": 0,
            "common_item_id": 0,
            "convert_piece_num": 0,
            "convert_common_item_num": 0,
            "additional_piece_num": 5 if ct == 1 else 0,
            "new_flag": 0,
            "win_prize": 0,
        })
        if ct == 1:
            add_pieces[cid] = add_pieces.get(cid, 0) + 5
    d["gacha_result_list"] = results
    rs = d.setdefault("reward_summary_info", {})
    rs["add_piece_list"] = [{"piece_id": k, "piece_num": n} for k, n in add_pieces.items()]
    rs["add_item_list"] = []
    rs["add_card_list"] = []
    rs["add_support_card_list"] = []
    d["bonus_item_array"] = []
    d["item_list"] = []
    if "limit_item_info" in d:
        d["limit_item_info"]["gacha_id"] = gacha_id
        d["limit_item_info"]["num"] = len(cards)
    return v


def make_dynamic_gacha(base_resp):
    """生成动态抽卡响应，返回 (declared, seq)。"""
    import msgpack as _mp
    import json as _json

    req_path = _latest_req_plain()
    info = _parse_gacha_req(req_path) if req_path else None
    gacha_id = (info or {}).get("gacha_id", 30476)
    draw = (info or {}).get("draw_type") or (info or {}).get("draw_num") or 1
    # draw_type: 1=单抽, 2=十连（常见约定）；也兼容 draw_num 直接给数量
    n = 10 if draw == 2 else (draw if isinstance(draw, int) and draw > 2 else 1)

    cards = _draw_cards(gacha_id, n)
    if not cards:
        return None

    resp = _build_gacha_response(gacha_id, cards, base_resp)
    data = _mp.packb(resp, use_bin_type=True)

    os.makedirs(DYNAMIC_DIR, exist_ok=True)
    seq = _dyn_seq[0] = _dyn_seq[0] + 1
    open(f"{DYNAMIC_DIR}/{seq}.msgpack", "wb").write(data)

    stat = {}
    for _, _, r in cards:
        stat[r] = stat.get(r, 0) + 1
    print(f"[srv] 抽卡 gacha_id={gacha_id} n={n} -> {stat} (seq={seq}, {len(data)} B)", flush=True)
    return (0xFFFF0000 + seq, seq)
'''

# 插到文件末尾的 main 之前
idx = s.find("def main():")
assert idx > 0, "找不到 main()"
s = s[:idx] + gacha_code + "\n\n" + s[idx:]

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("已插入抽卡生成模块")
