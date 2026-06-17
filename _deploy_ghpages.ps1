$ErrorActionPreference = "Stop"
$repo = "xiaokangjiao-ai/x-gudao"
$outputDir = "$PSScriptRoot\output"

function gh {
    $r = @(& gh api @args 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "gh api failed: $r" }
    return $r -join "`n"
}

# Get current gh-pages
Write-Host "Step 1: Getting current gh-pages SHA..."
$branchInfo = gh "/repos/$repo/branches/gh-pages" | ConvertFrom-Json
$baseSha = $branchInfo.commit.sha
$baseTree = $branchInfo.commit.commit.tree.sha
Write-Host "  base_sha=$($baseSha.Substring(0,8)) base_tree=$($baseTree.Substring(0,8))"

# Collect files
Write-Host "Step 2: Collecting files..."
$files = @()
Get-ChildItem $outputDir -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($outputDir.Length + 1).Replace('\', '/')
    $files += @{ rel=$rel; path=$_.FullName }
}
Write-Host "  Found $($files.Count) files"

# Create blobs
Write-Host "Step 3: Creating blobs..."
$blobMap = @{}
foreach ($f in $files) {
    $content = [Convert]::ToBase64String([IO.File]::ReadAllBytes($f.path))
    $body = @{
        content = $content
        encoding = "base64"
    } | ConvertTo-Json -Compress
    $blob = gh "--method" "POST" "/repos/$repo/git/blobs" "--field" "content=$content" "--field" "encoding=base64" | ConvertFrom-Json
    $blobMap[$f.rel] = $blob.sha
    Write-Host "  $($f.rel): $($blob.sha.Substring(0,8))"
}

# Add .nojekyll
$njContent = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(""))
$njBlob = gh "--method" "POST" "/repos/$repo/git/blobs" "--field" "content=$njContent" "--field" "encoding=base64" | ConvertFrom-Json
Write-Host "  .nojekyll: $($njBlob.sha.Substring(0,8))"

# Build tree
Write-Host "Step 4: Creating tree..."
$treeItems = @()
foreach ($f in $files) {
    $treeItems += @{
        path = $f.rel
        mode = "100644"
        type = "blob"
        sha  = $blobMap[$f.rel]
    }
}
$treeItems += @{
    path = ".nojekyll"
    mode = "100644"
    type = "blob"
    sha  = $njBlob.sha
}

$treeData = @{
    tree = $treeItems
    base_tree = $baseTree
} | ConvertTo-Json -Compress -Depth 10

# Use gh api with raw input
$treeJson = gh "--method" "POST" "/repos/$repo/git/trees" "--input" "-" <<< $treeData | ConvertFrom-Json
$newTree = $treeJson.sha
Write-Host "  new_tree=$($newTree.Substring(0,8))"

# Create commit
Write-Host "Step 5: Creating commit..."
$commitData = @{
    message = "deploy: 22 detail pages - full financial data + AI analysis"
    tree = $newTree
    parents = @($baseSha)
} | ConvertTo-Json -Compress

$commitJson = gh "--method" "POST" "/repos/$repo/git/commits" "--input" "-" <<< $commitData | ConvertFrom-Json
$newCommit = $commitJson.sha
Write-Host "  new_commit=$($newCommit.Substring(0,8))"

# Update branch ref
Write-Host "Step 6: Updating gh-pages..."
$refData = @{ sha = $newCommit } | ConvertTo-Json -Compress
gh "--method" "PATCH" "/repos/$repo/git/refs/heads/gh-pages" "--input" "-" <<< $refData | Out-Null

Write-Host ""
Write-Host "Done! https://xiaokangjiao-ai.github.io/x-gudao/" -ForegroundColor Green
