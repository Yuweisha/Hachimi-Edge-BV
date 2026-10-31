"""把 note/index 的 sid 与 servertime 同步成 load/index 的（字节级等长替换）。

sid 是 42 字符 str8（d9 2a），等长替换不动结构。
servertime 是 uint32（ce），等长替换。
"""
import json
import shutil
import struct
import sys

REPLAY = r"C:/Users/Schwarz/uma_replay/replay.bin"
DECL = r"C:/Users/Schwarz/uma_replay/path_declared.json"
LOAD_DECL = 1214003
NOTE_DECL = 347866

KEY_SID = b"\xa3" + b"sid"      # fixstr(3) + sid
KEY_ST = b"\xaa" + b"servertime"


def main() -> int:
    shutil.copy(REPLAY, REPLAY + ".bak_sid")

    b = open(REPLAY, "rb").read()
    n = struct.unpack_from("<I", b, 4)[0]
    off = 8
    items = {}
    for _ in range(n):
        a, decl, dl = struct.unpack_from("<III", b, off)
        off += 12
        items[decl] = b[off:off + dl]
        off += dl

    load = items[LOAD_DECL]
    note = bytearray(items[NOTE_DECL])

    # 从 load 取 sid 和 servertime
    lsid = None
    lst = None
    i = load.find(KEY_SID)
    if i >= 0 and load[i + 4] == 0xD9:
        ln = load[i + 5]
        lsid = load[i + 6:i + 6 + ln]
        print(f"load sid ({ln}): {lsid.decode()}")
    i = load.find(KEY_ST)
    if i >= 0 and load[i + len(KEY_ST)] == 0xCE:
        lst = struct.unpack_from(">I", load, i + len(KEY_ST) + 1)[0]
        print(f"load servertime: {lst}")

    # 替换 note 里的
    if lsid:
        i = note.find(KEY_SID)
        if i >= 0 and note[i + 4] == 0xD9:
            ln = note[i + 5]
            old = bytes(note[i + 6:i + 6 + ln])
            print(f"note sid ({ln}): {old.decode()}")
            if ln == len(lsid):
                note[i + 6:i + 6 + ln] = lsid
                print("  sid 已替换（等长）")
            else:
                print(f"  长度不同（{ln} vs {len(lsid)}），跳过")

    if lst is not None:
        i = note.find(KEY_ST)
        if i >= 0 and note[i + len(KEY_ST)] == 0xCE:
            old = struct.unpack_from(">I", note, i + len(KEY_ST) + 1)[0]
            struct.pack_into(">I", note, i + len(KEY_ST) + 1, lst)
            print(f"  servertime: {old} -> {lst}")

    items[NOTE_DECL] = bytes(note)
    o = bytearray(b"RPLY") + struct.pack("<I", len(items))
    for decl, data in sorted(items.items()):
        o += struct.pack("<III", decl, decl, len(data)) + data
    open(REPLAY, "wb").write(o)
    print(f"replay.bin: {len(items)} 条, {len(o)} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
