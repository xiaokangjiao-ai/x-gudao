import sqlite3, os, json
db = sqlite3.connect(os.path.join(r'C:\Users\Administrator\x-gudao', 'data', 'market_data.db'))
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", tables)
for t in tables:
    count = db.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
    print(f"  {t[0]}: {count} rows")

# Check overview.json
ov = json.load(open(os.path.join(r'C:\Users\Administrator\x-gudao', 'output', 'overview.json')))
print(f"\noverview.json has {len(ov.get('tickers', ov.get('items', [])))} items")
# Print keys of first item
if 'tickers' in ov:
    items = ov['tickers']
elif 'items' in ov:
    items = ov['items']
else:
    items = list(ov.values())[:1]
if items:
    print("First item keys:", list(items[0].keys()))
    print("First item:", json.dumps(items[0], indent=2)[:500])
