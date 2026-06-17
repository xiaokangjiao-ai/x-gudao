#!/usr/bin/env python3
"""Deploy output/ to gh-pages using gh api."""
import subprocess, json, os, base64
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
REPO = "xiaokangjiao-ai/x-gudao"

def gh_raw(method, endpoint, data=None):
    args = ["gh", "api", "--method", method, endpoint]
    with Path(ROOT / "_tmp_payload.json").open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    args += ["--input", str(ROOT / "_tmp_payload.json")]
    result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        raise Exception(f"gh failed ({method} {endpoint}): {result.stderr}")
    return result.stdout

# Step 1: Get current gh-pages
print("Step 1: Getting current gh-pages SHA...")
branch_info = json.loads(gh_raw("GET", f"/repos/{REPO}/branches/gh-pages"))
base_sha = branch_info["commit"]["sha"]
base_tree = branch_info["commit"]["commit"]["tree"]["sha"]
print(f"  base_sha={base_sha[:8]} base_tree={base_tree[:8]}")

# Step 2: Collect files
print("Step 2: Collecting files...")
files = []
for root_dir, dirs, filenames in os.walk(OUTPUT):
    for fname in filenames:
        fpath = Path(root_dir) / fname
        rel = str(fpath.relative_to(OUTPUT)).replace("\\", "/")
        files.append(rel)
# Add .nojekyll
files.append(".nojekyll")
print(f"  Found {len(files)} files")

# Step 3: Create blobs
print("Step 3: Creating blobs...")
blob_map = {}
for i, rel in enumerate(files):
    if rel == ".nojekyll":
        content = ""
    else:
        content = base64.b64encode((OUTPUT / rel).read_bytes()).decode()
    blob = json.loads(gh_raw("POST", f"/repos/{REPO}/git/blobs", {"content": content, "encoding": "base64"}))
    blob_map[rel] = blob["sha"]
    print(f"  [{i+1}/{len(files)}] {rel}: {blob['sha'][:8]}")

# Step 4: Create tree (batch in chunks of 100, GitHub limit)
print("Step 4: Creating tree...")
tree_items = [{"path": rel, "mode": "100644", "type": "blob", "sha": blob_map[rel]} for rel in files]
tree_data = {"tree": tree_items, "base_tree": base_tree}
tree_json_str = gh_raw("POST", f"/repos/{REPO}/git/trees", tree_data)
new_tree = json.loads(tree_json_str)["sha"]
print(f"  new_tree={new_tree[:8]}")

# Step 5: Create commit
print("Step 5: Creating commit...")
commit_data = {
    "message": "deploy: 22 detail pages - full financial data + AI analysis\n\nSSG pages for all ETF/stock tickers with financial metrics, charts, and AI analysis.",
    "tree": new_tree,
    "parents": [base_sha]
}
commit_json_str = gh_raw("POST", f"/repos/{REPO}/git/commits", commit_data)
new_commit = json.loads(commit_json_str)["sha"]
print(f"  new_commit={new_commit[:8]}")

# Step 6: Update ref
print("Step 6: Updating gh-pages...")
gh_raw("PATCH", f"/repos/{REPO}/git/refs/heads/gh-pages", {"sha": new_commit})
print("  Done!")

# Cleanup
(ROOT / "_tmp_payload.json").unlink(missing_ok=True)
print()
print("[OK] gh-pages updated! Visit: https://xiaokangjiao-ai.github.io/x-gudao/")
