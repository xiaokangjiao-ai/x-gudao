import os, socket, ssl, time
os.environ['https_proxy'] = 'http://127.0.0.1:7890'
os.environ['http_proxy'] = 'http://127.0.0.1:7890'
import urllib.request

ips = [
    "140.82.112.4", "140.82.113.4", "140.82.114.4", "140.82.121.4",
    "20.205.243.166", "20.205.243.161", "20.205.243.164",
    "192.30.255.112", "192.30.255.113",
    "185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153",
    "13.250.177.223", "52.228.155.138",
]
for ip in ips:
    t = time.time()
    try:
        # use proxy to connect to https://<ip> with Host header github.com
        req = urllib.request.Request(f"https://{ip}/", headers={'Host': 'github.com', 'User-Agent': 'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=12)
        d = r.read(200)
        print(f"OK   {ip}  status={r.status}  t={round(time.time()-t,1)}")
    except Exception as e:
        print(f"FAIL {ip}  t={round(time.time()-t,1)}  {repr(e)[:80]}")
