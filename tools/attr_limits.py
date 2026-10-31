"""游戏内属性合法上限（用户实测确认）。"""

MAX_ATTR = {
    "speed": 2287,
    "stamina": 1850,
    "power": 1825,
    "wiz": 1815,
    "guts": 1700,
}

# race_entry 里的字段名映射
_FIELD_MAP = {
    "speed": "speed",
    "stamina": "stamina",
    "power": "pow",
    "wiz": "wiz",
    "guts": "guts",
}


def clamp_attr(key: str, value) -> int:
    """把单个属性夹到合法范围。key 用 max_attr 的键名（speed/stamina/power/wiz/guts）。"""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 0
    cap = MAX_ATTR.get(key)
    if cap is None:
        return max(0, v)
    return max(0, min(v, cap))


def clamp_horse(h: dict) -> dict:
    """就地修正 race_entry / trained_chara 里的五维。"""
    for k, cap in MAX_ATTR.items():
        fk = _FIELD_MAP[k]
        if fk in h and h[fk] is not None:
            h[fk] = clamp_attr(k, h[fk])
    return h


def is_legal(h: dict) -> bool:
    for k in MAX_ATTR:
        fk = _FIELD_MAP[k]
        v = h.get(fk)
        if v is not None and int(v) > MAX_ATTR[k]:
            return False
    return True
