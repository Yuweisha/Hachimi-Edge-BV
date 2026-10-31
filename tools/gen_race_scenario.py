"""生成 race_scenario（比赛剧本）的骨架。

结构（两份真实数据交叉验证）：
    头部 32 B
        [0:4]   = 4
        [4:8]   = 100000005   SIMULATE_DATA_VERSION_100000005
        [8:12]  = float       未定（54.5 / 64.87）
        [12:16] = 马数
        [16:20] = 12          每马每帧字节
        [20:24] = 0
        [24:28] = 帧数
        [28:32] = 每帧字节 = 4 + 马数×12
    帧数据（帧数 × 每帧字节）
        每帧：4 B 时间戳(float) + 马数 × 12 B
        每匹马 12 B = float Distance + u32(Lane<<16|300) + u32(0xff00<<16|HP)
    尾部 ~15.5 KB
        赛道事件，生成时整段拷贝录制那份

用法：
    sc = build_race_scenario(template_bytes, horses)
    # template_bytes = gzip.decompress(base64.b64decode(race_scenario))
"""
from __future__ import annotations

import gzip
import struct

FRAME_DT = 1.0 / 15.0        # 每帧 0.0666 秒（实测）
HEADER_SIZE = 32
HORSE_BYTES = 12


def parse_header(plain: bytes) -> dict:
    h = struct.unpack_from("<8I", plain, 0)
    return {
        "magic": h[0],
        "version": h[1],
        "param": struct.unpack_from("<f", plain, 8)[0],
        "n_horse": h[3],
        "horse_bytes": h[4],
        "frames": h[6],
        "frame_bytes": h[7],
    }


def split_parts(plain: bytes) -> tuple[bytes, bytes, bytes]:
    """拆成 (头部, 帧区, 尾部)。"""
    hd = parse_header(plain)
    body_end = HEADER_SIZE + hd["frames"] * hd["frame_bytes"]
    return plain[:HEADER_SIZE], plain[HEADER_SIZE:body_end], plain[body_end:]


def read_horse_frame(plain: bytes, frame: int, horse: int, hd: dict) -> dict:
    """读某帧某匹马。"""
    off = HEADER_SIZE + frame * hd["frame_bytes"] + 4 + horse * HORSE_BYTES
    dist = struct.unpack_from("<f", plain, off)[0]
    w1, w2 = struct.unpack_from("<II", plain, off + 4)
    return {
        "distance": dist,
        "lane": w1 & 0xFFFF,
        "lane_hi": w1 >> 16,
        "hp": w2 & 0xFFFF,
        "hp_hi": w2 >> 16,
    }


def build_race_scenario(template: bytes, distances: list[list[float]],
                        hp: list[list[int]] | None = None) -> bytes:
    """按模板生成新剧本。

    template   : gzip 解压后的原始明文（提供头部参数和尾部）
    distances  : distances[horse][frame] = 距离（米）
    hp         : hp[horse][frame] = HP 值；None 则沿用模板

    返回：gzip 压缩后的字节（可直接 base64 塞回响应）
    """
    hd = parse_header(template)
    n_horse = hd["n_horse"]
    frames = hd["frames"]
    head = bytearray(template[:HEADER_SIZE])
    tail = split_parts(template)[2]

    buf = bytearray(head)
    for fi in range(frames):
        # 帧头时间戳沿用模板（原值不是简单的 fi×0.0666，别自己算）
        src_ts = struct.unpack_from("<f", template, HEADER_SIZE + fi * hd["frame_bytes"])[0]
        buf += struct.pack("<f", src_ts)
        for hi in range(n_horse):
            src = read_horse_frame(template, fi, hi, hd)
            d = distances[hi][fi] if hi < len(distances) and fi < len(distances[hi]) else src["distance"]
            h = hp[hi][fi] if hp and hi < len(hp) and fi < len(hp[hi]) else src["hp"]
            buf += struct.pack("<f", float(d))
            buf += struct.pack("<HH", src["lane"], src["lane_hi"])
            buf += struct.pack("<HH", 0xFF00, int(h) & 0xFFFF)
    buf += tail
    return gzip.compress(bytes(buf), mtime=0)


def demo_uniform_speed(template: bytes, speeds: list[float]) -> bytes:
    """按恒定速度重算距离（用于验证客户端是否信任剧本）。"""
    hd = parse_header(template)
    frames = hd["frames"]
    out: list[list[float]] = []
    for v in speeds:
        out.append([v * fi * FRAME_DT for fi in range(frames)])
    return build_race_scenario(template, out)


if __name__ == "__main__":
    import base64
    import json
    import sqlite3
    import sys
    from pathlib import Path

    db = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/Schwarz/uma_replay/offline.db")
    con = sqlite3.connect(str(db))
    r = con.execute("SELECT data FROM response_cache WHERE path='ultimate_race/race_start'").fetchone()
    con.close()
    if not r:
        print("库里没有 ultimate_race/race_start")
        raise SystemExit(1)

    import msgpack
    obj = msgpack.unpackb(r[0], raw=False, strict_map_key=False, unicode_errors="replace")
    plain = gzip.decompress(base64.b64decode(obj["data"]["race_scenario"]))
    hd = parse_header(plain)
    print("头部:", hd)
    print("帧 0 马 0:", read_horse_frame(plain, 0, 0, hd))
    print("帧 100 马 0:", read_horse_frame(plain, 100, 0, hd))
