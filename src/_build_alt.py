import json
pwd = "dc769708-e255-4483-808e-4d68fe3f6556"
nodes = [
    ("CuteCloud-A", "52.228.155.138"),
    ("CuteCloud-B", "135.234.55.141"),
]
proxies = []
names = []
for name, srv in nodes:
    proxies.append({"name": name, "server": srv, "sni": "live.hwoss.cn", "skip": False})
    names.append(name)
lines = ["mixed-port: 7890", "allow-lan: false", "mode: global", "log-level: info", "proxies:"]
for p in proxies:
    lines.append('  - name: "' + p["name"] + '"')
    lines.append("    type: trojan")
    lines.append("    server: " + p["server"])
    lines.append("    port: 443")
    lines.append("    password: " + pwd)
    lines.append("    sni: " + p["sni"])
    lines.append("    skip-cert-verify: false")
    lines.append("    udp: true")
lines.append("proxy-groups:")
lines.append("  - name: PROXY")
lines.append("    type: select")
lines.append("    proxies: [" + ", ".join('"' + n + '"' for n in names) + "]")
lines.append("rules:")
lines.append("  - MATCH,PROXY")
open("clash_alt.yaml", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("wrote clash_alt.yaml", names)
