#!/bin/bash
set -e
REPO="xiaokangjiao-ai/x-gudao"
OUTPUT_DIR="output"
cd "$(dirname "$0")"

echo "Getting current gh-pages SHA..."
BRANCH_JSON=$(gh api /repos/$REPO/branches/gh-pages)
BASE_SHA=$(echo $BRANCH_JSON | python3 -c "import sys,json; print(json.load(sys.stdin)['commit']['sha'])")
BASE_TREE=$(echo $BRANCH_JSON | python3 -c "import sys,json; print(json.load(sys.stdin)['commit']['commit']['tree']['sha'])")
echo "base_sha=$BASE_SHA base_tree=$BASE_TREE"

# Create blobs and build tree JSON
TREE_ITEMS="[]"
BLOB_SHAS=""

for file in $(find "$OUTPUT_DIR" -type f | sed "s|$OUTPUT_DIR/||"); do
    content_b64=$(base64 -w0 "$OUTPUT_DIR/$file" 2>/dev/null || base64 "$OUTPUT_DIR/$file")
    blob_json=$(gh api --method POST /repos/$REPO/git/blobs \
        --field content="$content_b64" \
        --field encoding=base64 2>/dev/null)
    sha=$(echo $blob_json | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")
    echo "blob: $file -> ${sha:0:8}"
    # Add to tree
    mode="100644"
    TREE_ITEMS=$(echo $TREE_ITEMS | python3 -c "
import sys,json
items=json.load(sys.stdin)
items.append({'path':'$file','mode':'$mode','type':'blob','sha':'$sha'})
print(json.dumps(items))
")
done

# Add .nojekyll if missing
if [ ! -f "$OUTPUT_DIR/.nojekyll" ]; then
    echo "" > "$OUTPUT_DIR/.nojekyll"
fi
content_b64=$(echo -n "" | base64)
blob_json=$(gh api --method POST /repos/$REPO/git/blobs \
    --field content="$content_b64" \
    --field encoding=base64 2>/dev/null)
sha=$(echo $blob_json | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")
TREE_ITEMS=$(echo $TREE_ITEMS | python3 -c "
import sys,json
items=json.load(sys.stdin)
items.append({'path':'.nojekyll','mode':'100644','type':'blob','sha':'$sha'})
print(json.dumps(items))
")

# Create tree
echo "Creating tree..."
tree_json=$(gh api --method POST /repos/$REPO/git/trees \
    --field tree="$TREE_ITEMS" \
    --field base_tree="$BASE_TREE" 2>/dev/null)
NEW_TREE=$(echo $tree_json | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")
echo "new_tree=$NEW_TREE"

# Create commit
echo "Creating commit..."
commit_json=$(gh api --method POST /repos/$REPO/git/commits \
    --field message="deploy: 22 detail pages - full financial data + AI analysis" \
    --field tree="$NEW_TREE" \
    --field parents[]="$BASE_SHA" 2>/dev/null)
NEW_COMMIT=$(echo $commit_json | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")
echo "new_commit=$NEW_COMMIT"

# Update branch
echo "Updating gh-pages..."
gh api --method PATCH /repos/$REPO/git/refs/heads/gh-pages \
    --field sha="$NEW_COMMIT" --field force=true 2>/dev/null

echo "Done! https://xiaokangjiao-ai.github.io/x-gudao/"
