import json
pwd = "dc769708-e255-4483-808e-4d68fe3f6556"
lines = ["mixed-port: 7890", "allow-lan: false", "mode: global", "log-level: info", "proxies:",
'  - name: "CuteCloud-B"',
"    type: trojan",
"    server: 135.234.55.141",
"    port: 443",
"    password: " + pwd,
"    sni: live.hwoss.cn",
"    skip-cert-verify: false",
"    udp: true",
"proxy-groups:",
"  - name: PROXY",
"    type: select",
'    proxies: ["CuteCloud-B"]',
"rules:",
"  - MATCH,PROXY"]
open("clash_B.yaml", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("wrote clash_B.yaml")
