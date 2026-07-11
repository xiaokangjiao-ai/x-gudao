$env:https_proxy="http://127.0.0.1:7890"
$env:http_proxy="http://127.0.0.1:7890"
Set-Location "C:\Users\Administrator\x-gudao\gh-pages"
$max = 6
for ($i = 1; $i -le $max; $i++) {
    Write-Host "=== attempt $i ==="
    $out = git -c http.proxy=http://127.0.0.1:7890 -c http.version=HTTP/1.1 -c http.postBuffer=524288000 -c http.lowSpeedLimit=1 -c http.lowSpeedTime=25 push origin gh-pages 2>&1
    $out | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PUSH SUCCEEDED on attempt $i"
        exit 0
    }
    Write-Host "attempt $i failed/uncertain, waiting 5s"
    Start-Sleep -Seconds 5
}
Write-Host "ALL ATTEMPTS DONE"
exit 1
