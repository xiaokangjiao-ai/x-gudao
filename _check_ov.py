import json, sys
sys.stdout.reconfigure(encoding='utf-8')
ov = json.load(open(r'C:\Users\Administrator\x-gudao\output\overview.json'))
for t in ov['tickers']:
    print(f'{t["ticker"]}: change_pct={t.get("change_pct")}')
