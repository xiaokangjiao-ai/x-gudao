import os, time, urllib.request
os.environ['https_proxy'] = 'http://127.0.0.1:7890'
os.environ['http_proxy'] = 'http://127.0.0.1:7890'
for url in ['https://github.com', 'https://api.github.com', 'https://raw.githubusercontent.com']:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    t = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=20)
        d = r.read(300)
        print('OK', url, r.status, 'read', len(d), 'time', round(time.time()-t, 1))
    except Exception as e:
        print('ERR', url, repr(e))
