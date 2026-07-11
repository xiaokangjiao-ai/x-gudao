import sqlite3, os
base = r"E:\Program Files\v2rayN-windows-64-SelfContained\v2rayN-windows-64-SelfContained"
db = os.path.join(base, "guiConfigs", "guiNDB.db")
c = sqlite3.connect(db)
cur = c.cursor()
cur.execute("SELECT Address, Port, Sni, Network, Security, Id FROM ProfileItem")
seen = {}
for row in cur.fetchall():
    addr, port, sni, net, sec, uid = row
    key = f"{addr}:{port}:{sni}"
    if key not in seen:
        seen[key] = (net, sec)
for k, v in sorted(seen.items()):
    print(k, "| net=", v[0], "sec=", v[1])
print("TOTAL distinct:", len(seen))
