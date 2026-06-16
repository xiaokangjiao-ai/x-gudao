import yfinance as yf
import time

print("Waiting 5s before request...")
time.sleep(5)

for sym in ['VOO', 'QQQ', 'SPY']:
    try:
        print(f"Fetching {sym}...")
        t = yf.Ticker(sym)
        d = t.history(period='1mo')
        if d.empty:
            print(f"  {sym}: EMPTY (still rate limited?)")
        else:
            print(f"  {sym}: {len(d)} rows, last close=${d['Close'].iloc[-1]:.2f}")
        time.sleep(3)
    except Exception as e:
        print(f"  {sym} ERROR: {e}")
        time.sleep(3)

print("DONE")
