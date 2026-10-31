"""按马匹属性生成 race_scenario 的距离曲线（名次的真正来源）。

关键发现（已验证）：
  * 每匹马每帧 12 字节 = 3 个 float：(时间, 距离, 0)
  * 名次 = 首次到达赛道距离（如 3200m）的帧号排序
  * finishTime 是**输出**字段，改它不影响名次

所以生成剧本只需：
  1. 用属性算出每匹马的速度曲线
  2. 积分得到距离曲线
  3. 写进帧数据的第 2 个 float
  4. 结果块的 finishTime/diff 按距离曲线补算（仅展示用）

用法：
  python gen_race_distance.py --base 0034 --players "3:2287:1850:1825:1700:1815" --distance 3200 --out gen.bin
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import math
import struct
from pathlib import Path

# ---- 速度模型（从实测 1118 条比赛记录标定）----
# 完赛时间与距离的关系：1600m≈92s, 2000m≈117s, 2400m≈142s, 3200m≈194s
# 平均速度随距离下降：1600m→17.6, 2000m→17.1, 2400m→16.9, 3200m→16.5
V_BASE = 17.6          # 1600m 基准速度 m/s
V_DIST_DECAY = 0.00035  # 每多 1 米速度衰减
V_SPEED_K = 0.18       # speed 属性影响（幂次，标定：2287→19.8m/s, 1400→16.2m/s）
SPURT_START = 0.72     # 冲刺起点（占全程比例）
SPURT_MULT = 1.16
START_ACCEL_FRAMES = 8   # 起跑加速帧数
HP_IMPACT = 0.15       # 耐力不足时的掉速比例


def base_speed(distance: float) -> float:
    """赛道基准速度（不含属性）。"""
    return V_BASE - (distance - 1600) * V_DIST_DECAY


def horse_speed_curve(speed: int, stamina: int, distance: float, nframe: int,
                      style: int = 2, motivation: int = 4) -> list[float]:
    """算一匹马每帧的速度（m/s）。"""
    base = base_speed(distance)
    # 属性影响：speed 相对 1000 的幂次修正
    base *= (max(speed, 100) / 1000.0) ** V_SPEED_K
    # 干劲
    base *= {1: 0.96, 2: 0.98, 3: 1.0, 4: 1.02, 5: 1.04}.get(motivation, 1.0)
    # 跑法：追马前期慢后期快
    style_curve = {
        1: (1.03, 0.97),   # 逃：起跑快，末段稍慢
        2: (1.00, 1.00),   # 先
        3: (0.97, 1.05),   # 差
        4: (0.94, 1.09),   # 追
    }
    early_m, late_m = style_curve.get(style, (1.0, 1.0))

    # 耐力：够跑完就有冲刺，不够就掉速
    hp_need = distance / base
    hp_have = (distance + 0.8 * 0.889 * max(stamina, 1)) / base
    can_spurt = hp_have >= hp_need * 0.92

    curve = []
    for f in range(nframe):
        p = f / max(1, nframe - 1)
        v = base * (early_m + (late_m - early_m) * p)
        # 起跑加速
        if f < START_ACCEL_FRAMES:
            v *= 0.35 + 0.65 * (f / START_ACCEL_FRAMES)
        # 冲刺
        if p > SPURT_START and can_spurt:
            k = (p - SPURT_START) / (1 - SPURT_START)
            v *= 1 + (SPURT_MULT - 1) * min(1.0, k * 1.5)
        # 耐力不足 → 末段掉速
        if not can_spurt and p > 0.8:
            v *= 1 - HP_IMPACT * (p - 0.8) / 0.2
        curve.append(v)
    return curve


def integrate(curve: list[float], dt: float) -> list[float]:
    """速度曲线 → 距离曲线。"""
    out = []
    d = 0.0
    for v in curve:
        d += v * dt
        out.append(d)
    return out


def solve_dt(speeds: list[float], distance: float, nframe: int) -> float:
    """求一个 dt，使最快的马刚好在 nframe 内跑完 distance。"""
    avg = sum(speeds) / max(1, len(speeds))
    return distance / (avg * nframe) * 1.02


def parse_players(s: str) -> dict[int, dict]:
    """'3:2287:1850:1825:1700:1815:4:4' → {3: {...}}"""
    out = {}
    for part in s.split(","):
        if not part.strip():
            continue
        f = part.split(":")
        pos = int(f[0])
        out[pos] = {
            "speed": int(f[1]) if len(f) > 1 else 1000,
            "stamina": int(f[2]) if len(f) > 2 else 1000,
            "power": int(f[3]) if len(f) > 3 else 1000,
            "guts": int(f[4]) if len(f) > 4 else 1000,
            "wiz": int(f[5]) if len(f) > 5 else 1000,
            "style": int(f[6]) if len(f) > 6 else 2,
            "motivation": int(f[7]) if len(f) > 7 else 4,
        }
    return out


def build(base_plain: bytes, players: dict[int, dict], distance: float) -> tuple[bytes, list]:
    """改写 base 剧本里指定马匹的距离曲线，返回 (新剧本, 到达帧列表)。"""
    plain = bytearray(base_plain)
    ver, sver, seed, nh, cs, s1, nf, fb = struct.unpack_from("<8I", plain, 0)
    assert cs == 12, f"charaSize 应为 12，实际 {cs}"

    # dt：让「基准速度的马」刚好在 nf 帧内跑完 distance
    dt = distance / base_speed(distance) / nf

    arrive = [None] * nh
    for k in range(nh):
        if k in players:
            p = players[k]
            curve = horse_speed_curve(p["speed"], p["stamina"], distance, nf,
                                      p["style"], p["motivation"])
        else:
            # 未指定的马：保持原剧本的距离曲线不动
            continue
        dists = integrate(curve, dt)
        for f in range(nf):
            off = 32 + f*fb + k*cs
            t_old, d_old, f3 = struct.unpack_from("<3f", plain, off)
            struct.pack_into("<3f", plain, off, f * dt, dists[f], f3)
        for f, d in enumerate(dists):
            if d >= distance:
                arrive[k] = f
                break

    # 未指定的马：从原距离曲线找到达帧
    for k in range(nh):
        if k in players:
            continue
        for f in range(nf):
            _, d, _ = struct.unpack_from("<3f", plain, 32 + f*fb + k*cs)
            if d >= distance:
                arrive[k] = f
                break
    return bytes(plain), arrive


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="录制目录里的 race_scenario.json 或 .bin")
    ap.add_argument("--players", required=True,
                    help="pos:speed:stamina:power:guts:wiz[:style[:motivation]] 逗号分隔")
    ap.add_argument("--distance", type=float, default=3200)
    ap.add_argument("--out", default="gen_scenario.bin")
    a = ap.parse_args()

    p = Path(a.base)
    if p.suffix == ".json":
        obj = json.loads(p.read_text(encoding="utf-8"))
        plain = gzip.decompress(base64.b64decode(obj["data"]["race_scenario"]))
    else:
        plain = p.read_bytes()

    players = parse_players(a.players)
    out, arrive = build(plain, players, a.distance)

    ver, sver, seed, nh, cs, s1, nf, fb = struct.unpack_from("<8I", out, 0)
    print(f"生成完成: {len(out):,} B  {nh}马 {nf}帧  赛道 {a.distance}m")
    order = sorted([k for k in range(nh) if arrive[k] is not None], key=lambda k: arrive[k])
    print(f"到达帧: {[(k, arrive[k]) for k in range(nh)]}")
    print(f"名次: {order}")
    for pos in players:
        if pos in order:
            print(f"  pos{pos} → 第 {order.index(pos)+1} 名")
        else:
            print(f"  pos{pos} → 未冲线（dt 或速度算错）")
    Path(a.out).write_bytes(out)


if __name__ == "__main__":
    main()
