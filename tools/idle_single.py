"""托管育成（idle_single_mode）服务器权威生成。

设计原则：
  - 客户端在 start 到 end 之间零请求，服务器完全掌控整段结果
  - 用录制样本当结构模板，数值全部随机化
  - 三个接口：pre_start / start / end

模板来源：hachimi/http/20261028_162128/ 的 019/020/021 三份 .res.json
"""
from __future__ import annotations

import copy
import json
import os
import random
import time
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / "idle_tpl"

# 默认全托时长（秒）。样本实测 3000 秒 = 50 分钟。
DEFAULT_DURATION = 60     # 测试用 1 分钟（正式值 3000 = 50 分钟）

# 五维上限（游戏内实际最大值）
MAX_ATTR = {"speed": 2222, "stamina": 1870, "power": 1836, "guts": 1704, "wiz": 1842}


def _load(name: str) -> dict | None:
    p = TEMPLATE_DIR / f"{name}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _rand_attr(rng: random.Random, key: str) -> int:
    """生成本次育成的属性值：偏向高区间，但每次不同。"""
    cap = MAX_ATTR[key]
    lo = int(cap * 0.55)
    return rng.randint(lo, cap)


def build_pre_start(duration: int = DEFAULT_DURATION) -> dict:
    """pre_start：返回「上次设置 + 预约比赛」。

    客户端用它渲染确认界面。没有历史时就给一份默认设置。
    """
    tpl = _load("pre_start")
    if tpl is not None:
        return copy.deepcopy(tpl)

    # 无模板时给最小合法结构
    return {
        "data_headers": {"result_code": 1, "servertime": int(time.time())},
        "data": {
            "last_idle_single_mode_start_info": {
                "continue_setting": {
                    "continue_flag": 1,
                    "not_continue_flag_below_g2": 0,
                    "not_continue_flag_unsuitable_race": 0,
                },
                "priority_skill_array": [],
                "training_policy_ground_type": 1,
                "training_policy_param_rate_set_id": 1,
            },
            "reserved_race_info": {
                "default_deck_num": 0,
                "needs_default_confirm": 1,
                "reserved_race_array": [],
            },
        },
        "response_code": 1,
    }


def build_start(card_id: int = 111401, duration: int = DEFAULT_DURATION,
                seed: int | None = None) -> dict:
    """start：建立育成中的角色，下发起止时间戳。

    客户端据此显示倒计时，期间不发任何请求。
    """
    rng = random.Random(seed if seed is not None else time.time_ns())

    tpl = _load("start")
    if tpl is None:
        raise RuntimeError(f"缺少模板 {TEMPLATE_DIR}/start.json")

    out = copy.deepcopy(tpl)
    data = out.setdefault("data", {})
    pi = data.setdefault("progress_info", {})

    now = int(time.time())
    pi["start_time"] = now
    pi["end_time"] = now + int(duration)

    ci = pi.get("chara_info")
    if isinstance(ci, dict):
        ci["card_id"] = card_id
        # 育成开始时属性归零，结束时才出结果
        for k in ("speed", "stamina", "power", "guts", "wiz"):
            if k in ci:
                ci[k] = 0

    # ★ 关键：add_trained_chara_array 是「继承源角色」的完整数据。
    #   客户端用它渲染继承信息和计算因子加成；缺这个字段会判失败。
    if not data.get("add_trained_chara_array"):
        data["add_trained_chara_array"] = []

    out.setdefault("data_headers", {})["servertime"] = now
    return out




def find_inherit_chara(load_index_obj: dict, tid: int) -> dict | None:
    """从 load/index 的 trained_chara 里按 id 找继承源角色。"""
    for x in load_index_obj.get("data", {}).get("trained_chara", []):
        if int(x.get("trained_chara_id", 0)) == int(tid):
            return x
    return None


def build_start_with_inherit(load_index_obj: dict, card_id: int,
                             succ_id_1: int, succ_obj_rental: dict | None = None,
                             duration: int = DEFAULT_DURATION,
                             seed: int | None = None) -> dict:
    """start：带继承源数据。

    args:
        load_index_obj    完整的 load/index 响应（含 trained_chara）
        succ_id_1         自己的继承源 trained_chara_id
        succ_obj_rental   租借的继承源（好友的），可为 None
    """
    out = build_start(card_id=card_id, duration=duration, seed=seed)

    added = []
    if succ_id_1:
        own = find_inherit_chara(load_index_obj, succ_id_1)
        if own:
            added.append(own)
    if isinstance(succ_obj_rental, dict) and succ_obj_rental:
        added.append(succ_obj_rental)

    out["data"]["add_trained_chara_array"] = added
    return out


def build_end(card_id: int = 111401, duration: int = DEFAULT_DURATION,
              seed: int | None = None) -> dict:
    """end：整段育成的最终结果（74 KB 级）。

    数值全部随机化，结构沿用模板，保证客户端能解析。
    """
    rng = random.Random(seed if seed is not None else time.time_ns())

    tpl = _load("end")
    if tpl is None:
        raise RuntimeError(f"缺少模板 {TEMPLATE_DIR}/end.json")

    out = copy.deepcopy(tpl)
    data = out.setdefault("data", {})
    end_info = data.setdefault("end_info", {})
    plog = data.setdefault("progress_log_info", {})

    now = int(time.time())

    # 1) 结果角色
    ci = end_info.get("chara_info")
    if isinstance(ci, dict):
        ci["card_id"] = card_id
        ci["create_time"] = now
        for k in ("max_speed", "max_stamina", "max_power", "max_guts", "max_wiz"):
            src = k.replace("max_", "")
            nv = _rand_attr(rng, src)
            ci[k] = nv
            if src in ci:
                ci[src] = nv
        # 名次/粉丝
        if "chara_grade" in ci:
            ci["chara_grade"] = rng.randint(6, 10)
        if "fans" in ci:
            ci["fans"] = rng.randint(80000, 700000)
        if "motivation" in ci:
            ci["motivation"] = rng.randint(1, 5)

    # 2) 属性增长（progress_log_info.event_gain_info）
    gi = plog.get("event_gain_info")
    if isinstance(gi, dict):
        for k in ("speed", "stamina", "power", "guts", "wiz"):
            if k in gi and isinstance(gi[k], dict):
                gi[k]["value"] = rng.randint(300, 2100)
                gi[k]["sign"] = 0
        for k in ("max_speed", "max_stamina", "max_power", "max_guts", "max_wiz"):
            if k in gi:
                gi[k] = _rand_attr(rng, k.replace("max_", ""))
        if "skill_point" in gi:
            gi["skill_point"] = rng.randint(1500, 4500)
        if "total_skill_point" in plog:
            plog["total_skill_point"] = rng.randint(3000, 8000)

    # 3) 奖励
    rsi = end_info.get("reward_summary_info")
    if isinstance(rsi, dict):
        if "add_fcoin" in rsi:
            rsi["add_fcoin"] = rng.randint(3000, 30000)
        if "add_total_fan" in rsi:
            rsi["add_total_fan"] = rng.randint(10000, 50000)
        if "add_present_num" in rsi:
            rsi["add_present_num"] = rng.randint(0, 3)

    # 4) 比赛历史：保留结构，只改时间戳
    rh = plog.get("race_history_array")
    if isinstance(rh, list):
        base = now - int(duration)
        for i, item in enumerate(rh):
            if isinstance(item, dict):
                for tk in ("race_start_time", "start_time", "race_time"):
                    if tk in item:
                        item[tk] = base + int(duration * (i + 1) / max(len(rh), 1))

    out.setdefault("data_headers", {})["servertime"] = now
    return out


def ensure_templates(src_dir: str | os.PathLike) -> int:
    """从抓包目录导入三份模板。返回导入数量。"""
    src = Path(src_dir)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {
        "pre_start": "019_idle_single_mode#pre_start.res.json",
        "start": "020_idle_single_mode#start.res.json",
        "end": "021_idle_single_mode#end.res.json",
    }
    n = 0
    for name, fname in mapping.items():
        s = src / fname
        if s.exists():
            dst = TEMPLATE_DIR / f"{name}.json"
            dst.write_text(s.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            n += 1
    return n


if __name__ == "__main__":
    D = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/hachimi/http/20261028_162128"
    n = ensure_templates(D)
    print(f"导入 {n} 份模板 → {TEMPLATE_DIR}")

    for name in ("pre_start", "start", "end"):
        p = TEMPLATE_DIR / f"{name}.json"
        print(f"  {name}: {p.stat().st_size if p.exists() else 0} B")

    # 自检
    import msgpack
    for fn in (build_pre_start, build_start, build_end):
        obj = fn()
        b = msgpack.packb(obj, use_bin_type=True)
        print(f"  {fn.__name__}() → {len(b)} B msgpack")
