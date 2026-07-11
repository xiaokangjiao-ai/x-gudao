import sqlite3, os
base = r"E:\Program Files\v2rayN-windows-64-SelfContained\v2rayN-windows-64-SelfContained"
db = os.path.join(base, "guiConfigs", "guiNDB.db")
c = sqlite3.connect(db)
cur = c.cursor()

print("=== SubItem ===")
cur.execute("SELECT * FROM SubItem")
cols = [d[0] for d in cur.description]
print("cols:", cols)
for row in cur.fetchall():
    d = dict(zip(cols, row))
    for k, v in d.items():
        s = str(v)
        if len(s) > 200: s = s[:200] + "..."
        print(f"  {k}: {s}")

print("\n=== ProfileExItem cols ===")
cur.execute("SELECT * FROM ProfileExItem LIMIT 1")
cols = [d[0] for d in cur.description]
print(cols)
print("\n=== ProfileExItem sample (first 3) ===")
cur.execute("SELECT * FROM ProfileExItem LIMIT 3")
for row in cur.fetchall():
    d = dict(zip(cols, row))
    for k, v in d.items():
        s = str(v)
        if len(s) > 300: s = s[:300] + "..."
        print(f"  {k}: {s}")
    print("  ----")
