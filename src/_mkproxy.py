import json, os

prefs_path = os.path.join(os.environ['APPDATA'], 'com.follow', 'CuteCloud', 'shared_preferences.json')
raw = open(prefs_path, encoding='utf-8').read()
data = json.loads(raw)
cfg = json.loads(data['flutter.config'])
remote = json.loads(data.get('flutter.auth.remote_config.cache', '{}'))

zone = next(iter(remote.get('zones', {}).values()))
bps = zone['bootstrapProxies']

proxies = []
for bp in bps:
    if not bp.get('enabled'):
        continue
    proxies.append({
        'name': bp['name'],
        'type': bp['type'],
        'server': bp['server'],
        'port': bp['port'],
        'password': bp['password'],
        'sni': bp.get('sni', bp['server']),
    })

names = [p['name'] for p in proxies]
lines = ['mixed-port: 7890', 'allow-lan: false', 'mode: global', 'log-level: info', 'proxies:']
for p in proxies:
    lines.append('  - name: ' + p['name'])
    lines.append('    type: ' + p['type'])
    lines.append('    server: ' + p['server'])
    lines.append('    port: ' + str(p['port']))
    lines.append('    password: ' + p['password'])
    lines.append('    sni: ' + p['sni'])
    lines.append('    skip-cert-verify: true')
    lines.append('    udp: false')
lines.append('proxy-groups:')
lines.append('  - name: PROXY')
lines.append('    type: select')
lines.append('    proxies: [' + ', '.join(names) + ']')
lines.append('rules:')
lines.append('  - MATCH,PROXY')

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clash_bootstrap.yaml')
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print("WROTE", out)
print("PROXIES:", names)
