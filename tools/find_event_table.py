"""找 event_data_array 的 data_id 对应 master 哪张表。"""
import sqlite3

MDB = r"C:/Users/Schwarz/AppData/LocalLow/Cygames/UmamusumePrettyDerby_Jpn/master/master.mdb"
con = sqlite3.connect(MDB)
cur = con.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print(f"共 {len(tables)} 张表")

target = 501001100
hits = []
for t in tables:
    try:
        cur.execute(f"PRAGMA table_info({t})")
        cols = [r[1] for r in cur.fetchall()]
        if "id" not in cols:
            continue
        cur.execute(f"SELECT COUNT(*) FROM {t} WHERE id = ?", (target,))
        if cur.fetchone()[0] > 0:
            hits.append((t, cols))
    except Exception:
        pass

print(f"\n含 id={target} 的表:")
for t, cols in hits:
    print(f"  {t}: {cols}")
con.close()
