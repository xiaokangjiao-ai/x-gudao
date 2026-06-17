import requests
key = 'naRnrOfu3bs7fuhOdpczaUpkpNafsN3g'
url = f'https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/2026-06-12/2026-06-16?adjusted=true&sort=asc&limit=10&apiKey={key}'
try:
    r = requests.get(url, timeout=15)
    print(f'Status: {r.status_code}')
    d = r.json()
    print(f'Results: {len(d.get("results", []))}')
    if d.get('results'):
        bar = d['results'][-1]
        from datetime import datetime, timezone, timedelta
        ts_sec = bar['t'] / 1000
        dt_utc = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
        dt_cst = dt_utc + timedelta(hours=8)
        print(f'Latest bar: date={dt_cst.strftime("%Y-%m-%d")} close={bar["c"]} vol={bar["v"]}')
except Exception as e:
    print(f'Error: {e}')
