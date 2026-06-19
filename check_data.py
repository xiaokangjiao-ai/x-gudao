import sqlite3

conn = sqlite3.connect('data/market_data.db')
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'JPM', 'V']

print("检查股票数据：")
for s in symbols:
    result = conn.execute('SELECT COUNT(*), MAX(date) FROM market_data WHERE ticker=?', (s,)).fetchone()
    print(f'{s}: 记录数={result[0]}, 最新日期={result[1]}')

conn.close()
