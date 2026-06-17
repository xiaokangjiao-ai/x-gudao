import sys
sys.path.insert(0, 'src')
import massive_fetcher as mf

# Test IEFA - one of the missing tickers
print("=== Testing IEFA ===")
rows, status = mf.fetch_ohlcv('IEFA', '2024-01-01', '2026-06-16')
print(f"Status: {status} | Rows: {len(rows)}")
if rows:
    print(f"  First: {rows[0]}")
    print(f"  Last:  {rows[-1]}")

print()
print("=== Testing IVV ===")
rows2, status2 = mf.fetch_ohlcv('IVV', '2024-01-01', '2026-06-16')
print(f"Status: {status2} | Rows: {len(rows2)}")
if rows2:
    print(f"  First: {rows2[0]}")
    print(f"  Last:  {rows2[-1]}")

print()
print("=== Testing VEA ===")
rows3, status3 = mf.fetch_ohlcv('VEA', '2024-01-01', '2026-06-16')
print(f"Status: {status3} | Rows: {len(rows3)}")
if rows3:
    print(f"  Last: {rows3[-1]}")
