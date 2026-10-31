import base64

BITS = (0x82, 0x83, 0x84, 0x85)

for name in ("note_trainer_note", "jukebox_draw_random_request", "note_save_voice"):
    body = open(rf"C:/Users/Schwarz/uma_replay/raw/{name}.raw", "rb").read()
    d = base64.b64decode(body)
    print(f"\n=== {name}: {len(d)} B ===")

    hits = []
    for i in range(len(d) - 2):
        if d[i] in BITS and 0xA0 <= d[i + 1] <= 0xBF:
            ln = d[i + 1] - 0xA0
            if i + 2 + ln <= len(d):
                key = d[i + 2:i + 2 + ln]
                if all(32 <= c < 127 for c in key):
                    hits.append((i, key.decode("ascii", "replace")))
    print("  msgpack map 特征:", hits[:5] if hits else "无")
    print("  前 16 字节:", d[:16].hex(" "))
    print("  唯一字节数(前64):", len(set(d[:64])))
