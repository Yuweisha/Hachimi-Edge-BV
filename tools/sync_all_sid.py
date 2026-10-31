"""全局 sid 同步：把 replay.bin 里所有响应的 sid 改成 start_session 那个。

sid 是 42 字符的 str8（d9 2a），等长替换，不改结构。
servertime 是 uint32（ce），也一起同步，避免「日期已变更」。
"""
from __future__ import annotations

import json
import struct
import sys

import msgpack

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"

KEY_SID = b"\xa3sid"
KEY_ST = b"\xaa" + b"servertime"


def find_sid(data: bytes):
    i = data.find(KEY_SID)
    if i >= 0 and data[i + 4] == 0xD9:
        ln = data[i + 5]
        return i, ln, data[i + 6:i + 6 + ln]
    return None


def find_st(data: bytes):
    i = data.find(KEY_ST)
    if i >= 0 and data[i + len(KEY_ST)] == 0xCE:
        return i, struct.unpack_from(">I", data, i + len(KEY_ST) + 1)[0]
    return None


def main() -> int:
    b = open(REPLAY, "rb").read()
    if b[:4] != b"RPLY":
        print("replay.bin 格式不对")
        return 1
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        src, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    # 基准：start_session（526 字节，含 resource_version）
    base = items.get(526)
    if not base:
        print("找不到 start_session（526）")
        return 1
    got = find_sid(base)
    if not got:
        print("start_session 里没找到 sid")
        return 1
    _, ln, sid = got
    st = find_st(base)
    stime = st[1] if st else None
    print(f"基准 sid ({ln}): {sid.decode()}")
    if stime is not None:
        print(f"基准 servertime: {stime}")

    changed = 0
    for decl, data in list(items.items()):
        if decl == 526:
            continue
        buf = bytearray(data)
        did = False

        g = find_sid(bytes(buf))
        if g:
            i, l2, old = g
            if l2 == ln and bytes(old) != sid:
                buf[i + 6:i + 6 + l2] = sid
                did = True

        if stime is not None:
            g2 = find_st(bytes(buf))
            if g2:
                i2, old_st = g2
                if old_st != stime:
                    struct.pack_into(">I", buf, i2 + len(KEY_ST) + 1, stime)
                    did = True

        if did:
            items[decl] = bytes(buf)
            changed += 1

    print(f"同步了 {changed} 条")

    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
