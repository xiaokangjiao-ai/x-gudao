import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
c = sqlite3.connect(r'C:\Users\Administrator\x-gudao\data\market_data.db')
total = c.execute('SELECT COUNT(*) FROM market_data').fetchone()[0]
print(f'Total rows: {total}')
dates = c.execute('SELECT MIN(date), MAX(date), COUNT(DISTINCT ticker) FROM market_data').fetchone()
print(f'Date range: {dates[0]} ~ {dates[1]}, {dates[2]} tickers')
for t in ['SPY','AAPL']:
    cnt = c.execute('SELECT COUNT(*) FROM market_data WHERE ticker=?', (t,)).fetchone()[0]
    d = c.execute('SELECT MIN(date), MAX(date) FROM market_data WHERE ticker=?', (t,)).fetchone()
    print(f'{t}: {cnt} rows, {d[0]} ~ {d[1]}')
