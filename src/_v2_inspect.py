import sqlite3, os, json
base = r"E:\Program Files\v2rayN-windows-64-SelfContained\v2rayN-windows-64-SelfContained"
db = os.path.join(base, "guiConfigs", "guiNDB.db")
c = sqlite3.connect(db)
cur = c.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("TABLES:", tables)
for t in tables:
    try:
        cur.execute(f"SELECT count(*) FROM '{t}'")
        n = cur.fetchone()[0]
        print(f"  {t}: {n} rows")
    except Exception as e:
        print(f"  {t}: err {e}")
# dump subscriptions
for t in ('Subscription', 'Subscriptions', 'Server', 'Servers', 'Profile'):
    try:
        cur.execute(f"SELECT * FROM '{t}' LIMIT 3")
        rows = cur.fetchall()
        if rows:
            cols = [d[0] for d in cur.description]
            print(f"\n=== {t} cols: {cols}")
            for row in rows:
                print("  ROW:", str(row)[:400])
    except Exception:
        pass
