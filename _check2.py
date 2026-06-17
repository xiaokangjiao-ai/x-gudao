import re
with open(r'C:\Users\Administrator\x-gudao\output\index.html', 'r', encoding='utf-8') as f:
    content = f.read()
# Find ETF_DATA and STOCK_DATA sections
etf_start = content.find('ETF_DATA')
stock_start = content.find('STOCK_DATA')
render_start = content.find('renderGrid')
print(f'ETF_DATA at {etf_start}, STOCK_DATA at {stock_start}, renderGrid at {render_start}')

# Find tickers in each section
etf_section = content[etf_start:stock_start]
stock_section = content[stock_start:render_start]
etf_tickers = re.findall(r'ticker:\s*"([\w.]+)"', etf_section)
stock_tickers = re.findall(r'ticker:\s*"([\w.]+)"', stock_section)
print('ETFs:', etf_tickers)
print('Stocks:', stock_tickers)
print(f'ETF count: {len(etf_tickers)}, Stock count: {len(stock_tickers)}')

# Check for NaN or $0
nan_count = content.count('NaN')
zero_price = content.count('$0.00')
print(f'NaN occurrences: {nan_count}, $0.00 occurrences: {zero_price}')
