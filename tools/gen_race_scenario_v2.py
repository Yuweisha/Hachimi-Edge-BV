"""按属性生成 race_scenario 的帧数据段（结构按 2026-10-27 实测校正）。

真实结构（18 马 / 199~203 帧 / 3200m 样本验证）：

    头部 42 B
        [0:4]   = 4
        [4:8]   = 100000005   SIMULATE_DATA_VERSION_100000005
        [8:12]  = seed (u32)
        [12:16] = 马数 charaNum
        [16:20] = 12          charaSize（每匹马每帧字节）
        [20:24] = 0
        [24:28] = 帧数 frameNum
        [28:32] = 每帧字节 = 4 + 马数×charaSize
        [32:42] = 填充
    帧数据：帧数 × 每帧字节
        每帧 = 马数 × 12 B  +  4 B 帧尾（递增 u32，疑似帧时间×10000）
    尾部：事件段（技能触发）+ 马结果段（名次/时间），原样拷贝

每匹马每帧 12 B = 6 个 u16：
    [0] Speed × 10
    [1] Hp
    [2] BlockFrontHorseIndex（0xff00 = 无阻挡）
    [3] ?
    [4] ?
    [5] LanePosition（恒定）

客户端只把 Speed 积分成距离，不做属性模拟 —— 填对 Speed/Hp 就能决定轨迹。

用法：
    python gen_race_scenario_v2.py --base race_scenario_practice.bin --out out.bin \
        --speed 1595 --stamina 941 --power 809 --guts 736 --wiz 1088 --distance 3200
"""
from __future__ import annotations

import argparse
import base64
import gzip
import math
import struct
from pathlib import Path

HEADER_SIZE = 42
HORSE_BYTES = 12
FRAME_TAIL = 4

STYLE_HP_COEF = {1: 1.00, 2: 0.889, 3: 0.95, 4: 1.05}
MOTIVATION_COEF = {1: 0.96, 2: 0.98, 3: 1.0, 4: 1.02, 5: 1.04}
CRUISE_BASE = 0.0
CRUISE_K = 0.0417           # 标定：sqrt(500×1595)=893 → 893×0.0417 ≈ 37.2 m/s = 实测巡航 1860/50
SPURT_MULT = 1.22
V_START = 6.0               # 起跑 m/s（实测字段 300 / 50）
DRAIN_K = 0.70              # 标定：199 帧内 HP 从 3869 掉到 0（帧 180 左右归零）
SPD_SCALE = 50.0            # Speed 字段 = m/s × 50（实测：巡航 1860/50=37.2 m/s，3200m 约 90 秒）
MIN_SPEED = 10.0            # HP 耗尽后的失速下限（实测末帧 500/50）
HP_ZERO_FRAME = 180         # 实测 HP 归零帧


def parse_header(plain: bytes) -> dict:
    ver, sver, seed, nhorse, csize, x20, nframe, fbytes, x32 = struct.unpack_from("<9I", plain, 0)
    return {"magic": ver, "version": sver, "seed": seed, "n_horse": nhorse,
            "horse_bytes": csize, "x20": x20, "frames": nframe,
            "frame_bytes": fbytes, "x32": x32}


def frame_offset(hd: dict, frame: int) -> int:
    return HEADER_SIZE + frame * hd["frame_bytes"]


def tail_offset(hd: dict) -> int:
    return HEADER_SIZE + hd["frames"] * hd["frame_bytes"]


def read_horse(plain: bytes, hd: dict, frame: int, horse: int) -> dict:
    off = frame_offset(hd, frame) + horse * hd["horse_bytes"]
    speed, hp, block, f3, f4, lane = struct.unpack_from("<6H", plain, off)
    return {"speed": speed, "hp": hp, "block": block, "f3": f3, "f4": f4, "lane": lane}


def calc_speeds(speed: int, power: int, motivation: int, nframe: int) -> list[float]:
    eff = speed * MOTIVATION_COEF.get(motivation, 1.0)
    cruise = CRUISE_BASE + math.sqrt(500 * eff) * CRUISE_K
    n_start = max(3, int(nframe * 0.12))
    n_mid = int(nframe * 0.72)
    out: list[float] = []
    for f in range(nframe):
        if f < n_start:
            v = V_START + (cruise - V_START) * (f / max(1, n_start - 1)) ** 0.8
        elif f < n_mid:
            v = cruise + 2.0 * math.sin(f * 0.05)
        else:
            t = (f - n_mid) / max(1, nframe - n_mid)
            v = cruise * (1.0 + (SPURT_MULT - 1.0) * min(1.0, t * 3.0))
        out.append(v)
    return out


def calc_hps(stamina: int, distance: int, style: int, speeds: list[float]) -> tuple[list[int], float]:
    hp_max = distance + 0.8 * STYLE_HP_COEF.get(style, 1.0) * stamina
    total = sum(speeds) or 1.0
    dt = distance / total * 4.0
    hp = hp_max
    out: list[int] = []
    for v in speeds:
        drain = DRAIN_K * ((v - 100.0 + 12.0) / 12.0) ** 2
        hp = max(0.0, hp - drain * dt)
        out.append(int(hp))
    return out, hp_max


def build(base: bytes, speeds: list[float], hps: list[int], horse: int = 0) -> bytes:
    hd = parse_header(base)
    if len(speeds) < hd["frames"] or len(hps) < hd["frames"]:
        raise ValueError(f"曲线长度不足：需要 {hd['frames']} 帧")
    buf = bytearray(base)
    for f in range(hd["frames"]):
        off = frame_offset(hd, f) + horse * hd["horse_bytes"]
        spd = max(0, min(65535, int(speeds[f] * SPD_SCALE)))
        hp = max(0, min(65535, int(hps[f])))
        struct.pack_into("<H", buf, off, spd)
        struct.pack_into("<H", buf, off + 2, hp)
    return bytes(buf)


def compress_b64(plain: bytes) -> str:
    return base64.b64encode(gzip.compress(plain, mtime=0)).decode()


def write_to_db(db_path: str, path: str, plain: bytes, distance: int = 3200) -> int:
    """把新剧本写回数据库某个接口的 race_scenario 字段。"""
    import sqlite3
    import msgpack
    con = sqlite3.connect(db_path, timeout=20)
    r = con.execute("SELECT data FROM response_cache WHERE path=?", (path,)).fetchone()
    if not r:
        raise SystemExit(f"库里没有 {path}")
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    obj["data"]["race_result_info"]["race_scenario"] = compress_b64(plain)
    blob = msgpack.packb(obj, use_bin_type=True)
    con.execute("UPDATE response_cache SET data=?, declared=? WHERE path=?", (blob, len(blob), path))
    con.execute("DELETE FROM path_declared WHERE path=?", (path,))
    con.execute("INSERT INTO path_declared(path, declared) VALUES(?,?)", (path, len(blob)))
    con.commit()
    con.close()
    return len(blob)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--db", default="")
    ap.add_argument("--path", default="practice_race/race_start")
    ap.add_argument("--speed", type=int, default=1000)
    ap.add_argument("--stamina", type=int, default=1000)
    ap.add_argument("--power", type=int, default=1000)
    ap.add_argument("--guts", type=int, default=1000)
    ap.add_argument("--wiz", type=int, default=1000)
    ap.add_argument("--distance", type=int, default=3200)
    ap.add_argument("--style", type=int, default=2)
    ap.add_argument("--motivation", type=int, default=3)
    ap.add_argument("--horse", type=int, default=0)
    a = ap.parse_args()

    base = Path(a.base).read_bytes()
    hd = parse_header(base)
    print(f"骨架：马数={hd['n_horse']} 帧数={hd['frames']} 每帧={hd['frame_bytes']} "
          f"尾部={len(base)-tail_offset(hd):,} B")

    speeds = calc_speeds(a.speed, a.power, a.motivation, hd["frames"])
    hps, hp_max = calc_hps(a.stamina, a.distance, a.style, speeds)

    print(f"HP 上限={hp_max:.0f}  速度 {min(speeds):.1f} ~ {max(speeds):.1f} m/s  HP末={hps[-1]}")

    # HP 真正归零后才掉速（实测：耐力见底前一直加速，最后几帧骤降）
    zero_from = next((i for i, h in enumerate(hps) if h == 0), None)
    if zero_from is not None:
        for i in range(zero_from, len(speeds)):
            decay = max(MIN_SPEED, speeds[i] * (0.55 ** (i - zero_from + 1)))
            speeds[i] = decay
        print(f"HP 归零于帧 {zero_from}，之后 {len(speeds)-zero_from} 帧内掉到 "
              f"{min(speeds[zero_from:]):.1f} m/s")

    out = build(base, speeds, hps, a.horse)
    if a.out:
        Path(a.out).write_bytes(out)
        print(f"已写出 {a.out}（{len(out):,} B）")
    if a.db:
        n = write_to_db(a.db, a.path, out, a.distance)
        print(f"已写回数据库 {a.path}：响应 {n:,} B")


if __name__ == "__main__":
    main()
