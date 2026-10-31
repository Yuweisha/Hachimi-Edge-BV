"""给 local_server.py 加上 event_id_chara_id 的动态生成（图鉴剧情回放）。

规律（从 master 实测得出）：
  event_id = (single_mode_story_data.event_category + 1) * 1000
  chara_id = single_mode_story_data.card_chara_id

请求里带 {chara_id, story_id, select_index}，
服务器读 reqplain 里最新的含 story_id 的请求，从 master 查 event_category，
生成 {event_id, chara_id, story_id, event_contents_info} 返回。

这是幂等补丁：重复跑只会插一次。
"""
import io

P = "C:/Users/Schwarz/projects/Hachimi-Edge/tools/local_server.py"
s = io.open(P, encoding="utf-8").read()

MARK = "# ===== 图鉴剧情回放（event_id_chara_id）动态生成 ====="
if MARK in s:
    print("补丁已存在，跳过")
    raise SystemExit(0)

# ---- 1) 在 _parse_gacha_req 之前插入工具函数 ----
anchor = "def _parse_gacha_req(path):"
assert anchor in s

blocks = '''# ===== 图鉴剧情回放（event_id_chara_id）动态生成 =====

def _latest_req_story():
    """取 reqplain 下最新的、含 story_id 的请求明文。"""
    try:
        import glob as _g
        import msgpack as _mp
        files = sorted(_g.glob(REQPLAIN_DIR + "/req_*.msgpack"),
                       key=os.path.getmtime, reverse=True)
        for f in files[:30]:
            try:
                v = _mp.unpackb(open(f, "rb").read(), raw=False,
                                strict_map_key=False, unicode_errors="replace")
            except Exception:
                continue
            if isinstance(v, dict) and "story_id" in v:
                return v
        return None
    except Exception:
        return None


def _story_meta(story_id: int):
    """从 master 查 (chara_id, event_category)。"""
    try:
        import sqlite3 as _sq
        con = _sq.connect(GACHA_DB, timeout=5)
        cur = con.cursor()
        cur.execute(
            "SELECT card_chara_id, event_category FROM single_mode_story_data WHERE story_id=?",
            (story_id,),
        )
        row = cur.fetchone()
        con.close()
        if row:
            return int(row[0]), int(row[1])
    except Exception as e:
        print("[srv] 查 story_meta 失败:", e, flush=True)
    return None, None


def make_event_content(story_id: int, select_index: int = 0):
    """按 story_id 生成图鉴回放响应。"""
    chara_id, cat = _story_meta(story_id)
    if chara_id is None:
        return None
    event_id = (cat + 1) * 1000
    return {
        "response_code": 1,
        "data_headers": {
            "result_code": 1,
            "servertime": int(time.time()),
        },
        "data": {
            "event_id": event_id,
            "chara_id": chara_id,
            "story_id": story_id,
            "event_contents_info": {
                "support_card_id": 0,
                "choice_array": [
                    {
                        "select_index_info_array": [
                            {"branch_number": 1, "select_index": 1}
                        ],
                        "receive_item_id": 0,
                        "target_race_id": 0,
                        "gain_select_id_index": 1,
                        "select_icon": 0,
                    }
                ],
                "month": 4,
                "race_id": 0,
            },
        },
    }


'''

s = s.replace(anchor, blocks + anchor, 1)

# ---- 2) 在 _serve 里加分支（放在抽卡分支之前）----
gacha_anchor = '''            # 抽卡：现场生成随机结果，写 dynamic/<declared>.msgpack
            if rel == "gacha/exec" and decl and decl > 0:'''
assert gacha_anchor in s

event_branch = '''            # 图鉴剧情回放：按请求里的 story_id 现场生成
            if "event_id_chara_id" in rel or rel.endswith("/play_event"):
                req = _latest_req_story()
                if req and isinstance(req.get("story_id"), int):
                    content = make_event_content(req["story_id"],
                                                 req.get("select_index") or 0)
                    if content:
                        import msgpack as _mp_ev
                        plain = _mp_ev.packb(content, use_bin_type=True)
                        body = struct.pack("<I", len(plain)) + b"\\x00" * 32 + plain
                        import base64 as _b64_ev
                        payload = _b64_ev.b64encode(body)
                        self.log_message(
                            "replay %s -> 现场生成（story_id=%s, event_id=%s）",
                            rel, req["story_id"], content["data"]["event_id"])
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-msgpack")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers()
                        self.wfile.write(payload)
                        return
                self.log_message("replay %s -> 没拿到 story_id，回退", rel)

''' + gacha_anchor

s = s.replace(gacha_anchor, event_branch, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("补丁已应用")
