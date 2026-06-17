#!/usr/bin/env python3
"""Deploy output/ to gh-pages using GitHub API via gh cli."""
import subprocess, base64, json, os, time
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
REPO = "xiaokangjiao-ai/x-gudao"

def gh(cmd):
    """Run gh CLI and return stdout."""
    result = subprocess.run(
        ["gh", "api", "--method", cmd[0].upper(), "-f", "query=" + cmd[1]] if isinstance(cmd[1], str) and cmd[0] in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH') else ["gh"] + cmd,
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        raise Exception(f"gh failed: {result.stderr}")
    return result.stdout

def gh_graphql(query, variables=None):
    """Run gh graphql query."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables:
        for k, v in variables.items():
            cmd.extend(["-f", f"{k}={v}"])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        raise Exception(f"gh graphql failed: {result.stderr}")
    return json.loads(result.stdout)

def gh_raw(method, path, data=None, headers=None):
    """Call GitHub API directly using gh token."""
    token_result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, cwd=ROOT)
    token = token_result.stdout.strip()
    import urllib.request, urllib.error
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data and isinstance(data, str):
        data = data.encode()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

print("Step 1: Get current gh-pages commit SHA...")
branch_info, status = gh_raw("GET", f"/repos/{REPO}/branches/gh-pages")
base_tree = branch_info["commit"]["commit"]["tree"]["sha"]
base_sha = branch_info["commit"]["sha"]
print(f"  base_tree={base_tree[:8]}, base_sha={base_sha[:8]}")

# Step 2: Collect all files
print("Step 2: Collect files from output/...")
files = []
for root, dirs, filenames in os.walk(OUTPUT):
    for fname in filenames:
        fpath = Path(root) / fname
        rel = fpath.relative_to(OUTPUT).as_posix()
        files.append((rel, fpath))
print(f"  Found {len(files)} files")

# Step 3: Create blobs
print("Step 3: Create blobs...")
blobs = {}
for rel, fpath in files:
    content = fpath.read_bytes()
    b64 = base64.b64encode(content).decode()
    data = json.dumps({"content": b64, "encoding": "base64"}).encode()
    resp, status = gh_raw("POST", f"/repos/{REPO}/git/blobs", data=data)
    blobs[rel] = resp["sha"]
    print(f"  {rel}: {resp['sha'][:8]}")

# Step 4: Create tree
print("Step 4: Create tree...")
tree_items = []
for rel, fpath in files:
    is_dir = "." not in rel.split("/")[-1] or rel.endswith("/")
    tree_items.append({
        "path": rel,
        "mode": "100644" if not is_dir else "040000",
        "type": "blob" if not is_dir else "tree",
        "sha": blobs[rel]
    })

# Handle .nojekyll and CNAME
for fname in [".nojekyll", "CNAME"]:
    fpath = OUTPUT / fname
    if fpath.exists():
        content = fpath.read_bytes()
        b64 = base64.b64encode(content).decode()
        data = json.dumps({"content": b64, "encoding": "base64"}).encode()
        resp, status = gh_raw("POST", f"/repos/{REPO}/git/blobs", data=data)
        tree_items.append({
            "path": fname,
            "mode": "100644",
            "type": "blob",
            "sha": resp["sha"]
        })
        print(f"  {fname}: {resp['sha'][:8]}")

tree_data = json.dumps({"tree": tree_items, "base_tree": base_tree}).encode()
resp, status = gh_raw("POST", f"/repos/{REPO}/git/trees", data=tree_data)
new_tree = resp["sha"]
print(f"  new_tree={new_tree[:8]}")

# Step 5: Create commit
print("Step 5: Create commit...")
commit_data = json.dumps({
    "message": "deploy: 22 detail pages - full financial data + AI analysis\n\nStatic site with all ETF/stock detail pages.",
    "tree": new_tree,
    "parents": [base_sha]
}).encode()
resp, status = gh_raw("POST", f"/repos/{REPO}/git/commits", data=commit_data)
new_commit = resp["sha"]
print(f"  new_commit={new_commit[:8]}")

# Step 6: Update branch ref
print("Step 6: Update gh-pages ref...")
ref_data = json.dumps({"sha": new_commit}).encode()
resp, status = gh_raw("PATCH", f"/repos/{REPO}/git/refs/heads/gh-pages", data=ref_data)
print(f"  Done! ref={resp['object']['sha'][:8]}")
print("\n✅ gh-pages updated! Visit: https://xiaokangjiao-ai.github.io/x-gudao/")
