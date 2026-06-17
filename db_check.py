import sqlite3, os
db = 'C:/Users/Administrator/x-gudao/data/market_data.db'
if not os.path.exists(db):
    print('DB not found'); exit()
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT ticker, COUNT(*) as cnt, MIN(date), MAX(date) FROM market_data GROUP BY ticker ORDER BY cnt DESC")
rows = cur.fetchall()
print(f'Total: {sum(r[1] for r in rows)} records, {len(rows)} tickers')
for r in rows: print(f'  {r[0]:8s} {r[1]:4d} rows  {r[2]} ~ {r[3]}')
conn.close()
