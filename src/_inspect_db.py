import sqlite3, os
db = os.path.join(os.environ.get('APPDATA',''), 'com.follow', 'CuteCloud', 'database.sqlite')
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
        if n > 0 and n < 10:
            cur.execute(f"SELECT * FROM '{t}' LIMIT 3")
            for row in cur.fetchall():
                print("    ", str(row)[:300])
    except Exception as e:
        print(f"  {t}: err {e}")
