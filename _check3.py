import re
with open(r'C:\Users\Administrator\x-gudao\output\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find ETF_DATA array start
idx = content.find('const ETF_DATA')
snippet = content[idx:idx+2000]
print(snippet[:2000])
print('\n\n=== STOCK_DATA ===')
idx2 = content.find('const STOCK_DATA')
snippet2 = content[idx2:idx2+2000]
print(snippet2[:2000])

# Find the ticker property pattern
tickers = re.findall(r'ticker:\s*"([A-Z]+)"', content)
print(f'\nAll tickers found: {tickers}')
