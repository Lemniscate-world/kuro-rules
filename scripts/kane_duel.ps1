# Kane duel harness — Track B automation (R115 stage 5 style, metric = bugs/min).
# Usage: .\scripts\kane_duel.ps1
# Prereq ONCE (interactive, 30s): kane-cli login   (token cached locally, never in repo)
# Everything after that is fully automated. Secrets: never hardcoded (R76/R101).

param(
  [string]$Objective = "Kuro Control Center, a local dashboard that displays tracked-repo hygiene metrics, a searchable and org-filterable project grid, an attention queue of alerts, memory vault entries, rule highlights, and a sync pulse panel, falling back to a static snapshot when the live API is unavailable",
  [string]$Refine = "add expired snapshot case, 500MB disk display case, and dirty-project case",
  [string]$OutDir = (Join-Path $env:TEMP "kane-duel"),
  [int]$MaxTestRuns = 3
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$report = @{ generated_at = (Get-Date).ToString("o"); phases = @{} }

# 0. Auth gate (fail fast, no silent skip — R7)
$balBefore = cmd /c "kane-cli balance 2>&1"
if ($balBefore -match "Not authenticated") {
  Write-Output "AUTH_GATE: run 'kane-cli login' once (interactive browser OAuth), then re-run this script. Nothing was consumed."
  exit 2
}
$report.phases["balance_before"] = ($balBefore -join "`n")

# 1. Generate (one turn, exits alone; --agent = NDJSON)
# NOTE: --files allowlists doc/image/audio/video only (.html/.js rejected),
# so we pass identical .txt copies from TEMP — repo untouched, R111 safe.
$ctxDir = Join-Path $OutDir "ctx"
New-Item -ItemType Directory -Force -Path $ctxDir | Out-Null
Copy-Item -Force "dashboard/index.html" (Join-Path $ctxDir "index.html.txt")
Copy-Item -Force "dashboard/app.js" (Join-Path $ctxDir "app.js.txt")
$ctxFiles = ((Join-Path $ctxDir "index.html.txt") + "," + (Join-Path $ctxDir "app.js.txt"))
$genLog = Join-Path $OutDir "01-generate.ndjson"
$sw = [Diagnostics.Stopwatch]::StartNew()
cmd /c "kane-cli generate ""$Objective"" --files ""$ctxFiles"" --scenario-limit 3 --per-scenario-limit 5 --agent > ""$genLog"" 2>&1"
$report.phases["generate_ms"] = $sw.ElapsedMilliseconds

# Extract req id from terminal event (last JSON line carrying an id + regex fallback)
$reqId = $null
$raw = Get-Content $genLog -Raw
foreach ($line in (Get-Content $genLog)) {
  try {
    $o = $line | ConvertFrom-Json
    foreach ($p in @("request_id", "req_id", "req")) {
      if ($o.PSObject.Properties[$p] -and $o.$p) { $reqId = [string]$o.$p }
    }
  } catch {}
}
if (-not $reqId) {
  $m = [regex]::Match($raw, '"request_id"\s*:\s*"?([A-Za-z0-9_-]+)"?')
  if ($m.Success) { $reqId = $m.Groups[1].Value }
}
if (-not $reqId) { Write-Output "GENERATE_PARSE_FAIL: no req id in $genLog"; exit 1 }
$report["req_id"] = $reqId
Write-Output "REQ_ID=$reqId"

# 2. Refine (one turn)
$refLog = Join-Path $OutDir "02-refine.ndjson"
$sw = [Diagnostics.Stopwatch]::StartNew()
cmd /c "kane-cli generate ""$Refine"" --refine --req $reqId --agent > ""$refLog"" 2>&1"
$report.phases["refine_ms"] = $sw.ElapsedMilliseconds

# 3. Save functional cases only (Kane rule) -> temp dir, repo stays clean
$saveDir = Join-Path $OutDir "tests"
$saveLog = Join-Path $OutDir "03-save.ndjson"
$sw = [Diagnostics.Stopwatch]::StartNew()
cmd /c "kane-cli generate --save --req $reqId --out ""$saveDir"" --agent > ""$saveLog"" 2>&1"
$report.phases["save_ms"] = $sw.ElapsedMilliseconds
$saved = Get-ChildItem -Recurse -Filter "*_test.md" -Path $saveDir -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
$report["saved_count"] = @($saved).Count

# 4. Run saved tests locally (free), bounded
$runMs = @(); $i = 0
foreach ($f in @($saved)) {
  if ($i -ge $MaxTestRuns) { break }
  $i++
  $rl = Join-Path $OutDir ("04-run-{0}.ndjson" -f $i)
  $sw = [Diagnostics.Stopwatch]::StartNew()
  cmd /c "kane-cli testmd run ""$f"" --agent > ""$rl"" 2>&1"
  $runMs += $sw.ElapsedMilliseconds
}
$report.phases["run_ms"] = $runMs

$balAfter = cmd /c "kane-cli balance 2>&1"
$report.phases["balance_after"] = ($balAfter -join "`n")

$reportPath = Join-Path $OutDir "duel_report.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding UTF8
Write-Output "DONE: $reportPath | saved=$($report.saved_count) | gen_ms=$($report.phases.generate_ms) refine_ms=$($report.phases.refine_ms) save_ms=$($report.phases.save_ms)"
