"""实测编辑器各页 refresh 耗时。"""
import sys
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import db_editor

DB = Path(r"C:/Users/Schwarz/uma_replay/offline.db")

root = tk.Tk()
root.withdraw()          # 不显示窗口

t0 = time.perf_counter()
app = db_editor.App(root, DB)
app.open_db()
print(f"open_db: {time.perf_counter()-t0:.2f}s")

tests = [
    ("refresh_chara", app.refresh_chara),
    ("refresh_card", app.refresh_card),
    ("refresh_cloth", app.refresh_cloth),
    ("refresh_item", app.refresh_item),
    ("refresh_event", app.refresh_event),
    ("refresh_pool", app.refresh_pool),
    ("refresh_gacha", app.refresh_gacha),
    ("refresh_layout", app.refresh_layout),
    ("refresh_cache", app.refresh_cache),
    ("refresh_account", app.refresh_account),
]

for name, fn in tests:
    t = time.perf_counter()
    try:
        fn()
        dt = time.perf_counter() - t
        flag = "  ← 慢" if dt > 0.5 else ""
        print(f"{name:<20} {dt:>7.3f}s{flag}")
    except Exception as e:
        print(f"{name:<20} ERROR {e}")

# 再来一轮，看是否第二次更快（缓存生效）
print("\n--- 第二轮 ---")
for name, fn in tests:
    t = time.perf_counter()
    try:
        fn()
        dt = time.perf_counter() - t
        flag = "  ← 慢" if dt > 0.5 else ""
        print(f"{name:<20} {dt:>7.3f}s{flag}")
    except Exception as e:
        print(f"{name:<20} ERROR {e}")

root.destroy()
