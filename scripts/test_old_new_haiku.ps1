# NEW-test evaluation on your main key (Claude Haiku via OpenRouter, from .env). About $0.01.
# Writes a full debug log (every model attempt, error and case) to data/private/eval-old/debug-haiku.jsonl.
#   powershell -ExecutionPolicy Bypass -File scripts\test_old_new_haiku.ps1
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
$log = "data/private/eval-old/debug-haiku.jsonl"
Remove-Item $log -ErrorAction SilentlyContinue
$env:CLUBOPS_DEBUG_LOG = $log
$opts = @("--facts", "data/private/d5/facts-learned.csv", "--systems", "clubops", "--only", "E01", "E02", "E03", "E10", "E18")
Copy-Item data/private/eval-old/new-aub-rules.json data/rulebook/aub-rules.json -Force
uv run python scripts/eval_plans.py --events data/private/d5/d5-events.csv @opts --out data/private/eval-old/new-haiku.md
Write-Host "`nRESULT:"; Get-Content data/private/eval-old/new-haiku.md | Select-String "^\| clubops"
Write-Host "`nPROBLEMS AND CASES (full log: $log):"
if (Test-Path $log) {
  Get-Content $log | ForEach-Object { $_ | ConvertFrom-Json } |
    Where-Object { $_.kind -in 'case', 'model_error' -or ($_.kind -eq 'http_attempt' -and ($_.outcome -ne 'http' -or $_.status -ge 400)) } |
    ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 4 }
} else { Write-Host "no log was written" }
