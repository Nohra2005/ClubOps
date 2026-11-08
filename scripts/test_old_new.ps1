# Free old-vs-new evaluation on the TEST_* key from .env. Run from the ClubOps folder:
#   powershell -ExecutionPolicy Bypass -File scripts\test_old_new.ps1
$model = "gemini-3.5-flash-lite"
Get-Content .env | Where-Object { $_ -match '^TEST_(API_KEY|BASE_URL)=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2; Set-Item "env:$k" $v.Trim() }
$env:CLUBOPS_API_KEY = $env:TEST_API_KEY
$env:CLUBOPS_BASE_URL = $env:TEST_BASE_URL
$env:CLUBOPS_MODEL = $model
$env:CLUBOPS_MODEL_MODE = "live"
$env:CLUBOPS_PRICE_IN_PER_MTOK = "0"
$env:CLUBOPS_PRICE_OUT_PER_MTOK = "0"
$opts = @("--facts", "data/private/d5/facts-learned.csv", "--systems", "clubops", "--only", "E01", "E02", "E03", "E10", "E18")
Write-Host "OLD test..."
Copy-Item data/private/eval-old/aub-rules.json data/rulebook/aub-rules.json -Force
uv run python scripts/eval_plans.py --events data/private/eval-old/events.csv @opts --out data/private/eval-old/old.md
Write-Host "NEW test..."
Copy-Item data/private/eval-old/new-aub-rules.json data/rulebook/aub-rules.json -Force
uv run python scripts/eval_plans.py --events data/private/d5/d5-events.csv @opts --out data/private/eval-old/new.md
Write-Host "`nOLD:"; Get-Content data/private/eval-old/old.md | Select-String "clubops"
Write-Host "NEW:"; Get-Content data/private/eval-old/new.md | Select-String "clubops"
