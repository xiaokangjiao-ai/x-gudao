import os, urllib.request
os.environ['https_proxy'] = 'http://127.0.0.1:7890'
os.environ['http_proxy'] = 'http://127.0.0.1:7890'
url = "https://services.cu-te.cn/link?token=8d16200e62d3000ebe69280d3185b6ad"
req = urllib.request.Request(url, headers={'User-Agent': 'v2rayN/1.0'})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        print("STATUS", resp.status, "LEN", len(data))
        text = data.decode('utf-8', errors='replace')
        with open("sub_raw.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("HEAD:", text[:600])
except Exception as e:
    print("ERR", repr(e))
