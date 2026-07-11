import re, urllib.parse, json

text = open("sub_decoded.yaml", "r", encoding="utf-8").read()
lines = [l.strip() for l in text.splitlines() if l.strip().startswith("trojan://")]

def unquote(s):
    try:
        return urllib.parse.unquote(s)
    except Exception:
        return s

proxies = []
names = []
for l in lines:
    m = re.match(r"trojan://([^@]+)@([^:]+):(\d+)\?(.*)#(.*)$", l)
    if not m:
        print("skip:", l[:60]); continue
    password = urllib.parse.unquote(m.group(1))
    server = m.group(2)
    port = int(m.group(3))
    qs = m.group(4)
    remark = unquote(m.group(5))
    params = dict(urllib.parse.parse_qsl(qs))
    sni = params.get("sni") or params.get("peer") or server
    allow_insecure = params.get("allowInsecure", "0")
    skip = (allow_insecure == "1")
    name = remark
    proxies.append({
        "name": name,
        "server": server,
        "port": port,
        "password": password,
        "sni": sni,
        "skip": skip,
    })
    names.append(name)

print(f"parsed {len(proxies)} trojan nodes")

lines_out = ["mixed-port: 7890", "allow-lan: false", "mode: global", "log-level: info", "proxies:"]
for p in proxies:
    lines_out.append("  - name: " + json.dumps(p["name"], ensure_ascii=False))
    lines_out.append("    type: trojan")
    lines_out.append("    server: " + p["server"])
    lines_out.append("    port: " + str(p["port"]))
    lines_out.append("    password: " + p["password"])
    lines_out.append("    sni: " + p["sni"])
    lines_out.append("    skip-cert-verify: " + ("true" if p["skip"] else "false"))
    lines_out.append("    udp: true")
lines_out.append("proxy-groups:")
lines_out.append("  - name: PROXY")
lines_out.append("    type: select")
lines_out.append("    proxies: [" + ", ".join(json.dumps(n, ensure_ascii=False) for n in names) + "]")
lines_out.append("rules:")
lines_out.append("  - MATCH,PROXY")

with open("clash_sub.yaml", "w", encoding="utf-8") as f:
    f.write("\n".join(lines_out) + "\n")
print("WROTE clash_sub.yaml with", len(proxies), "nodes")
